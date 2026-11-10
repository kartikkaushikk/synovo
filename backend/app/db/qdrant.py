from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_qdrant_client() -> AsyncQdrantClient:
    # Create a new client per call to avoid cross-event-loop reuse in Celery workers.
    return AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=30,
    )


async def _create_collection(client: AsyncQdrantClient) -> None:
    """Create the collection and its payload indexes from scratch."""
    await client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=Distance.COSINE,
        ),
    )
    await client.create_payload_index(
        collection_name=settings.QDRANT_COLLECTION,
        field_name="job_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    await client.create_payload_index(
        collection_name=settings.QDRANT_COLLECTION,
        field_name="speaker_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )


async def ensure_collection() -> None:
    """
    Idempotently ensure the Qdrant collection exists with the correct
    vector dimension.

    If the collection already exists but has a different dimension (e.g. a
    stale 768-dim collection left over from a previous model), it is deleted
    and recreated with the current EMBEDDING_DIM.  All existing vectors are
    lost, but they were incompatible anyway.
    """
    client = get_qdrant_client()
    try:
        existing = await client.get_collections()
        names = [c.name for c in existing.collections]

        if settings.QDRANT_COLLECTION not in names:
            logger.info(
                "qdrant_collection_creating",
                collection=settings.QDRANT_COLLECTION,
                dim=settings.EMBEDDING_DIM,
            )
            await _create_collection(client)
            return

        # Collection exists — validate vector dimension.
        info = await client.get_collection(collection_name=settings.QDRANT_COLLECTION)
        vectors_cfg = getattr(getattr(info, "config", None), "params", None)
        existing_dim = getattr(getattr(vectors_cfg, "vectors", None), "size", None)

        if existing_dim is not None and existing_dim != settings.EMBEDDING_DIM:
            logger.warning(
                "qdrant_dim_mismatch_recreating",
                collection=settings.QDRANT_COLLECTION,
                existing_dim=existing_dim,
                expected_dim=settings.EMBEDDING_DIM,
            )
            # Drop the stale collection and rebuild with the correct dim.
            await client.delete_collection(collection_name=settings.QDRANT_COLLECTION)
            await _create_collection(client)
        else:
            logger.debug(
                "qdrant_collection_ok",
                collection=settings.QDRANT_COLLECTION,
                dim=existing_dim,
            )
    finally:
        await client.close()
