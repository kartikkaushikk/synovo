import uuid
import time
import os
import re
import unicodedata
import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from app.core.config import settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)
def _sanitize_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    # Normalize to ASCII and keep a safe subset of characters.
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    if not name:
        name = "upload"
    ext = re.sub(r"[^A-Za-z0-9._-]+", "", ext)
    return f"{name}{ext}"



def _get_s3_client():
    access_key = settings.S3_ACCESS_KEY or settings.AWS_ACCESS_KEY_ID
    secret_key = settings.S3_SECRET_KEY or settings.AWS_SECRET_ACCESS_KEY
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


async def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload file to S3/R2 and return the object URL."""
    safe_filename = _sanitize_filename(filename)
    key = f"audio/{uuid.uuid4()}/{safe_filename}"
    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        base_url = (settings.S3_PUBLIC_URL or settings.S3_ENDPOINT_URL).rstrip("/")
        url = f"{base_url}/{settings.S3_BUCKET}/{key}"
        logger.info("file_uploaded", key=key, size_bytes=len(file_bytes))
        return url
    except (BotoCoreError, ClientError) as e:
        raise StorageError(str(e))


async def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    try:
        s3 = _get_s3_client()
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as e:
        raise StorageError(str(e))


async def download_file(url: str) -> bytes:
    """Download a file from S3/R2 by URL."""
    import httpx
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content
