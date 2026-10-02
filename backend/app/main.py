import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import router
from backend.app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title="Alzhio",
    version="1.0.0",
    description="Local longitudinal MRI research prototype. Not a medical diagnosis.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins.split(","):
            return JSONResponse({"detail": "This request origin is not allowed."}, status_code=403)
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > settings.max_upload_bytes + 1024 * 1024):
        return JSONResponse({"detail": "Request exceeds the upload limit."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    fields = [".".join(str(v) for v in error["loc"][1:]) for error in exc.errors()]
    return JSONResponse(
        status_code=422, content={"detail": "Check the following fields: " + ", ".join(fields)}
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger(__name__).exception("Request failed", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "The local service could not complete this request. Check service logs and retry."
        },
    )


app.include_router(router)
