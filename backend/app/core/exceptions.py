from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class CIPException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class JobNotFound(CIPException):
    def __init__(self, job_id: str):
        super().__init__(f"Job {job_id} not found", status_code=404)


class JobFailed(CIPException):
    def __init__(self, job_id: str, reason: str):
        super().__init__(f"Job {job_id} failed: {reason}", status_code=422)


class StorageError(CIPException):
    def __init__(self, detail: str):
        super().__init__(f"Storage error: {detail}", status_code=503)


class EmbeddingError(CIPException):
    def __init__(self, detail: str):
        super().__init__(f"Embedding error: {detail}", status_code=503)


class SearchError(CIPException):
    def __init__(self, detail: str):
        super().__init__(f"Search error: {detail}", status_code=503)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CIPException)
    async def cip_exception_handler(request: Request, exc: CIPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "type": type(exc).__name__},
        )
