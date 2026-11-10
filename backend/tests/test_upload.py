"""Tests for /api/v1/upload and /api/v1/jobs endpoints."""
import io
import uuid
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_invalid_type(client: AsyncClient):
    """Non-audio file should be rejected with 422."""
    file_content = b"not an audio file"
    resp = await client.post(
        "/api/v1/upload",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code in (400, 415, 422)


@pytest.mark.asyncio
async def test_upload_valid(client: AsyncClient):
    """Valid audio MIME should create a job (mocking storage + celery)."""
    fake_audio = b"RIFF" + b"\x00" * 100   # minimal WAV-like header
    fake_job_id = str(uuid.uuid4())

    with (
        patch("app.api.v1.routes.upload.upload_file", new_callable=AsyncMock) as mock_store,
        patch("app.api.v1.routes.upload.create_job", new_callable=AsyncMock) as mock_create,
        patch("app.api.v1.routes.upload.dispatch_pipeline") as mock_dispatch,
    ):
        mock_store.return_value = f"s3://cip-audio/{fake_job_id}.audio"
        mock_create.return_value = MagicMock(id=uuid.UUID(fake_job_id), status="pending")
        mock_dispatch.return_value = "celery-task-id"

        resp = await client.post(
            "/api/v1/upload",
            files={"file": ("interview.mp3", io.BytesIO(fake_audio), "audio/mpeg")},
        )

    assert resp.status_code in (200, 202)
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient):
    """Unknown job ID should return 404."""
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient):
    """Jobs list endpoint should be available for the dashboard."""
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
