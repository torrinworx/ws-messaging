import os
import json
import inspect
import asyncio
import pathlib
import traceback
import importlib.util
from functools import wraps
from fastapi import WebSocket


def job(name: str = None):
    def annotator(f):
        f._job_meta = {"name": name}

        @wraps(f)
        async def async_handler(*args, **kwargs):
            return await f(*args, **kwargs)

        @wraps(f)
        def sync_handler(*args, **kwargs):
            return f(*args, **kwargs)

        return async_handler if asyncio.iscoroutinefunction(f) else sync_handler

    return annotator


class Jobs:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Jobs, cls).__new__(cls)
            cls.__instance.__init_once(*args, **kwargs)
        return cls.__instance

    def __init_once(self, dir_path="."):
        if getattr(self, "_is_initialized", False):
            return
        self._is_initialized = True

        self.directory = os.path.abspath(dir_path)
        self.jobs = []
        self._get_jobs()

    def _get_jobs(self):
        job_files = self._find_job_files()
        for filepath in job_files:
            self._load_jobs_from_file(filepath)

    def _find_job_files(self):
        return [
            filepath
            for filepath in pathlib.Path(self.directory, "backend", "jobs").rglob(
                "*.py"
            )
            if filepath.name != "__init__.py"
        ]

    def _load_jobs_from_file(self, filepath):
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)

        if spec.loader:
            spec.loader.exec_module(module)
            self._extract_jobs_from_module(module)

    def _extract_jobs_from_module(self, module):
        for attr in dir(module):
            fn = getattr(module, attr)
            if callable(fn) and hasattr(fn, "_job_meta"):
                job_info = getattr(fn, "_job_meta")
                description = fn.__doc__ if fn.__doc__ else ""
                self.jobs.append(
                    {
                        "title": job_info.get("title", fn.__name__),
                        "description": job_info.get("description", description),
                        "function": fn,
                    }
                )

    async def job_handler(self, msg, ws: WebSocket):
        """
        Handles job execution requests received over a WebSocket connection.

        Args:
            payload: The data received from the WebSocket client.
            ws: The WebSocket connection instance.

        Returns:
            Sends the execution result or error message back over the WebSocket connection.
        """

        payload = json.loads(msg)
        job_name = payload.get("title")
        job_item = next(
            (job for job in self.jobs if job.get("title") == job_name), None
        )

        if not job_item:
            await ws.send_text(
                json.dumps(
                    {"status": "error", "message": f"Job '{job_name}' not found."}
                )
            )
            return

        try:
            job_func = job_item.get("function")
            params = inspect.signature(job_func).parameters

            context_args = {
                "payload": payload,
                "ws": ws,
            }
            provided_args = payload.get("args", {})

            # Include context_args if **kwargs is acceptable
            if any(
                param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()
            ):
                provided_args.update(context_args)
            else:  # Include only specified args
                for arg_key, arg_val in context_args.items():
                    if arg_key in params:
                        provided_args[arg_key] = arg_val

            if inspect.iscoroutinefunction(job_func):
                result = await job_func(**provided_args)
            else:
                result = job_func(**provided_args)

            await ws.send_text(json.dumps(result))
        except Exception as ex:
            print(traceback.format_exc())
            await ws.send_text(
                json.dumps(
                    {
                        "status": "error",
                        "message": f"Job '{job_name}' encountered an error: {str(ex)}",
                    }
                )
            )
