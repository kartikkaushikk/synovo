import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger

router = APIRouter(prefix="/ws", tags=["streaming"])
logger = get_logger(__name__)


@router.websocket("/stream/{session_id}")
async def stream_transcription(websocket: WebSocket, session_id: str):
    """
    Real-time transcription via WebSocket.

    Protocol:
      - Client sends: binary PCM frames (16 kHz, 16-bit, mono)
      - Server sends: JSON {"type": "transcript", "text": "...", "is_final": bool, "t": float}

    The StreamTranscriber uses module-level model singletons so the first
    request may be slow (model warm-up) but all subsequent connections are
    instant.
    """
    await websocket.accept()
    logger.info("ws_connected", session_id=session_id)

    # Import here so the module-level singletons (loaded at startup via
    # prewarm_stream_models) are already warm by the time the first connection
    # arrives.  If they are not warm yet, _get_whisper_model() /
    # _get_vad_model() will load them now (this blocks the calling thread
    # but we run it in an executor so the event loop stays free).
    from ai.transcription.stream_engine import StreamTranscriber

    loop = asyncio.get_event_loop()

    # Initialise the transcriber in a thread so model loading (if not already
    # cached) does not block the event loop.
    transcriber: StreamTranscriber = await loop.run_in_executor(
        None, StreamTranscriber
    )

    try:
        while True:
            # Wait for next PCM chunk from the browser (30 s idle timeout)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_bytes(), timeout=30.0
                )
            except asyncio.TimeoutError:
                await websocket.send_json(
                    {"type": "error", "message": "Connection timed out due to inactivity."}
                )
                break

            # Process the chunk in a thread (CPU-bound Whisper/VAD work)
            result = await loop.run_in_executor(
                None, transcriber.process_chunk, data
            )

            if result:
                await websocket.send_json(
                    {
                        "type": "transcript",
                        "text": result["text"],
                        "is_final": result["is_final"],
                        "t": result["timestamp"],
                        "session_id": session_id,
                    }
                )
                logger.info(
                    "ws_transcript",
                    session_id=session_id,
                    text_preview=result["text"][:60],
                )

    except WebSocketDisconnect:
        logger.info("ws_disconnected", session_id=session_id)

    except Exception as exc:
        logger.error("ws_error", session_id=session_id, error=str(exc))
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close(code=1011)
        except Exception:
            pass  # socket may already be closed

    finally:
        await loop.run_in_executor(None, transcriber.cleanup)
        logger.info("ws_cleanup_done", session_id=session_id)
