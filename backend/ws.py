import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from global_vars import jobs

logger = logging.getLogger("uvicorn")
router = APIRouter()

async def get_job(websocket: WebSocket):
    buffer = bytearray()
    job_name = None
    params = {}

    try:
        async for chunk in websocket.iter_bytes():
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning("Client disconnected before job could be read")
                return None, None, None

            buffer.extend(chunk)
            if len(buffer) >= 8:
                job_name_bytes = buffer[:8]
                job_name = job_name_bytes.decode("utf-8").strip()
                remaining_bytes = buffer[8:]
                
                try:
                    params = json.loads(remaining_bytes.decode("utf-8"))
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error decoding parameters: {e}")
                break
    except Exception as e:
        logger.error(f"Exception in get_job: {e}")
        return None, None, None

    async def data_stream():
        if remaining_bytes:
            yield remaining_bytes
        async for chunk in websocket.iter_bytes():
            yield chunk

    return job_name, params, data_stream

@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning("WebSocket disconnected unexpectedly.")
                break

            job_name, params, data_stream = await get_job(websocket)
            if not job_name:
                continue

            if job_name:
                await jobs.job_handler(ws=websocket, data_stream=data_stream, job_name=job_name, params=params)
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as ex:
        logger.error(f"Exception occurred: {ex}")
        try:
            await websocket.send_text(f"Error: {str(ex)}")
        except WebSocketDisconnect:
            logger.warning("WebSocket closed while sending an error message.")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        logger.info("WebSocket connection closed.")
