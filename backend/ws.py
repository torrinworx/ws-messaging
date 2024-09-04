import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from global_vars import jobs

logger = logging.getLogger("uvicorn")
router = APIRouter()


async def get_job(websocket: WebSocket):
    """
    Read the first 8 bytes to get job name and subsequent bytes for parameters.

    Returns the job name, parameters, and remaining bytes in stream.
    """
    buffer = bytearray()
    job_name = None
    params = {}

    async for chunk in websocket.iter_bytes():
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

    async def remaining_data_stream():
        if remaining_bytes:
            yield remaining_bytes

        async for chunk in websocket.iter_bytes():
            yield chunk

    return job_name, params, remaining_data_stream


@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # TODO: Keep the websocket open and going, allow for any number of
        # streamed requests in a single open websocket without the need to
        # reopen it.
        # Ideally in the scinario of a website, the websocket should only
        # open when the user loads the page.
        job_name, params, data_stream = await get_job(websocket)

        if job_name:
            await jobs.job_handler(
                ws=websocket,
                data_stream=data_stream(),
                job_name=job_name,
                params=params,
            )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as ex:
        logger.error(f"Exception occurred: {ex}")
        try:
            await websocket.send_text(f"Error: {str(ex)}")
        except WebSocketDisconnect:
            logger.warning("WebSocket closed while sending error message.")
    finally:
        await websocket.close()
        logger.info("WebSocket connection closed.")
