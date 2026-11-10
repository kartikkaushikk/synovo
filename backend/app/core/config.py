from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Conversational Intelligence Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Postgres
    POSTGRES_URL: str = "postgresql+asyncpg://cip:cip@postgres:5432/cip"
    POSTGRES_URL_SYNC: str = "postgresql://cip:cip@postgres:5432/cip"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_RESULT_BACKEND: str = "redis://redis:6379/1"

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "transcript_chunks"

    # Storage (S3 / Cloudflare R2 / Supabase S3)
    S3_ENDPOINT_URL: str = ""
    S3_PUBLIC_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "cip-audio"
    S3_REGION: str = "auto"

    # AI Models
    WHISPER_MODEL_SIZE: str = "large-v3"
    WHISPER_DEVICE: str = "cpu"          # "cuda" on GPU hosts
    WHISPER_COMPUTE_TYPE: str = "int8"   # "float16" on GPU hosts
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    NLI_MODEL: str = "cross-encoder/nli-deberta-v3-base"
    HUGGINGFACE_TOKEN: str = ""   # Required for pyannote/speaker-diarization-3.1
    ENABLE_CPU_DIARIZATION: bool = True  # pyannote is very memory-heavy on CPU/local Docker

    # Celery
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_TASK_SOFT_LIMIT: int = 1800  # 30 min

    # Semantic Cache
    CACHE_SIMILARITY_THRESHOLD: float = 0.92
    CACHE_TTL_SECONDS: int = 3600

    # Chunking
    CHUNK_MAX_TOKENS: int = 512
    CHUNK_OVERLAP_RATIO: float = 0.20

    # Contradiction Detection
    CONTRADICTION_MIN_GAP_S: float = 120.0   # 2-min minimum gap between chunks
    CONTRADICTION_TOP_K: int = 10
    CONTRADICTION_SCORE_THRESHOLD: float = 0.50


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
