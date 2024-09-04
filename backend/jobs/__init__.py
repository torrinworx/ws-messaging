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
        params: dict,
    ):
        """
        Handles job execution requests received from a binary stream.

        Args:
            ws: The WebSocket connection instance.
            data_stream: The raw binary stream iterable generator from the WebSocket.
            job_name: The name of the job from the first 8 bits of the stream.
            params: The params of the job from the stream.
        Returns:
            Streams the function returned values and job execution verification.
            If the function doesn't return anything, it only returns the job execution verification.
        """
        try:
            job = next((job for job in self.jobs if job.get("name") == job_name), None)
            if not job:
                await ws.send_bytes(
                    json.dumps(
                        {"status": "error", "message": f"Job '{job_name}' not found."}
                    ).encode('utf-8')
                )
                return

            job_func = job.get("function")
            sig_params = inspect.signature(job_func).parameters

            mutable_params = {
                k: v.default
                for k, v in sig_params.items()
                if v.default is not inspect.Parameter.empty
            }
            mutable_params.update(params)

            context_params = {
                "data_stream": data_stream,
                "ws": ws,
            }

            if any(
                param.kind == inspect.Parameter.VAR_KEYWORD
                for param in sig_params.values()
            ):
                mutable_params.update(context_params)
            else:
                for arg_key, arg_val in context_params.items():
                    if arg_key in sig_params:
                        mutable_params[arg_key] = arg_val

            if inspect.iscoroutinefunction(job_func):
                result = await job_func(**mutable_params)
            else:
                result = job_func(**mutable_params)

            if inspect.isgenerator(result) or inspect.isasyncgen(result):
                async for item in result:
                    await ws.send_bytes(
                        json.dumps({"result": item, "status": "success"}).encode('utf-8')
                    )
            else:
                await ws.send_bytes(
                    json.dumps(
                        {"result": result, "status": "success", "message": "Succeeded."}
                    ).encode('utf-8')
                )
        except json.JSONDecodeError:
            await ws.send_bytes(
                json.dumps(
                    {"status": "error", "message": "Failed to decode the data as JSON."}
                ).encode('utf-8')
            )
        except Exception as ex:
            print(traceback.format_exc())
            await ws.send_bytes(
                json.dumps(
                    {
                        "status": "error",
                        "message": f"Job '{job_name}' encountered an error: {str(ex)}",
                    }
                ).encode('utf-8')
            )
