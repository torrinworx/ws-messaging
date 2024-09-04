import os
import json
import typing
import base64
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
                        "name": job_info.get("name", fn.__name__),
                        "description": job_info.get("description", description),
                        "function": fn,
                    }
                )

    async def job_handler(
            self,
            ws: WebSocket,
            data_stream: typing.AsyncGenerator[bytes, None],
            job_name: str,
            params: dict
        ):
        """
        Handles job execution requests received from a binary stream.

        Args:
            ws: The WebSocket connection instance.
            data_stream: The raw binary stream iterable generator from the Websocket.
            job_name: The name of the job from the first 8 bits of the stream.

        Returns:
            By default, streams the function returned values, and job execution verification,
            if the funciton doesn't return anything, then it only returns the job execution verification.
        """
        try:
            job = next((job for job in self.jobs if job.get("name") == job_name), None)

            if not job:
                # TODO: Send bytes/standard message format somehow:
                await ws.send_bytes(json.dumps({
                    "status": "error",
                    "message": f"Job '{job_name}' not found."
                }))
                return

            job_func = job.get("function")
            params = inspect.signature(job_func).parameters

            context_params = {
                "data_stream": data_stream,
                "ws": ws,
            }

            # Include context_params if **kwargs is acceptable
            if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()):
                params.update(context_params)
            else:  # Include only specified params
                for arg_key, arg_val in context_params.items():
                    if arg_key in params:
                        params[arg_key] = arg_val

            if inspect.iscoroutinefunction(job_func):
                result = await job_func(**params)
            else:
                result = job_func(**params)

            await ws.send_bytes(json.dumps({
                'result': result,
                'status': 'success',
                'message': 'Succeded.'
            }))
        except json.JSONDecodeError:
            await ws.send_bytes(json.dumps({
                "status": "error",
                "message": "Failed to decode the data as JSON."
            }))
        except Exception as ex:
            print(traceback.format_exc())
            await ws.send_bytes(json.dumps({
                "status": "error",
                "message": f"Job '{job_name}' encountered an error: {str(ex)}",
            }))
