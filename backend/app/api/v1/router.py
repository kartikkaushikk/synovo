from fastapi import APIRouter
from app.api.v1.routes import upload, jobs, search, stream, reports

router = APIRouter(prefix="/api/v1")

router.include_router(upload.router)
router.include_router(jobs.router)
router.include_router(search.router)
router.include_router(stream.router)
router.include_router(reports.router)
