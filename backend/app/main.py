import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import router as v1_router
from app.db.postgres import engine, Base
from app.db.qdrant import ensure_collection


def _prewarm_stream_models() -> None:
    """Load Whisper + Silero VAD singletons in the background at startup.
    Runs in a thread so it doesn't block the async event loop."""
    try:
        from ai.transcription.stream_engine import _get_whisper_model, _get_vad_model
        _get_whisper_model()
        _get_vad_model()
    except Exception as exc:
        # Non-fatal: models will be lazily loaded on first WebSocket connection
        get_logger("startup").warning("stream_prewarm_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.DEBUG)
    logger = get_logger("startup")

    # Create all tables (Alembic handles migrations in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("postgres_tables_ready")

    # Ensure Qdrant collection exists
    await ensure_collection()
    logger.info("qdrant_collection_ready", collection=settings.QDRANT_COLLECTION)

    # Pre-warm Whisper + Silero VAD in background (non-blocking)
    # This means the first WebSocket connection will be fast instead of
    # waiting 30+ seconds for models to load.
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _prewarm_stream_models)
    logger.info("stream_models_prewarming_in_background")

    logger.info("startup_complete", version=settings.APP_VERSION)
    yield

    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://localhost(:\d+)?|https?://127\.0\.0\.1(:\d+)?|https://.*\.railway\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(v1_router)


@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/", tags=["infra"])
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}
