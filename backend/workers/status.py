from __future__ import annotations

import asyncio
import threading

from app.core.config import settings
from app.models.job import JobStatus


def set_job_status(
    job_id: str,
    status: JobStatus,
    progress: int | None = None,
    stage: str | None = None,
    error_msg: str | None = None,
) -> None:
    async def _update() -> None:
        import asyncpg

        dsn = settings.POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        try:
            assignments = ["status = $2::jobstatus"]
            values: list[object] = [job_id, status.name]
            if progress is not None:
                values.append(progress)
                assignments.append(f"progress = ${len(values)}")
            if stage is not None:
                values.append(stage)
                assignments.append(f"current_stage = ${len(values)}")
            if error_msg is not None:
                values.append(error_msg)
                assignments.append(f"error_msg = ${len(values)}")
            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                assignments.append("completed_at = NOW()")

            await conn.execute(
                f"UPDATE jobs SET {', '.join(assignments)} WHERE id = $1::uuid",
                *values,
            )
        finally:
            await conn.close()

    def _run_in_new_loop() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_update())
        finally:
            loop.close()

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop and running_loop.is_running():
        thread = threading.Thread(target=_run_in_new_loop, daemon=True)
        thread.start()
        thread.join()
    else:
        _run_in_new_loop()
