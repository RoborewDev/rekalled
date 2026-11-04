from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code: int = 400

    def __init__(self, detail: str, **extra: str) -> None:
        super().__init__(detail)
        self.detail: str = detail
        self.extra: dict[str, str] = extra


class NotFoundError(DomainError):
    status_code: int = 404


class SourceTooLongError(DomainError):
    status_code: int = 413


class GenerationFailedError(DomainError):
    status_code: int = 502


class QuotaExceededError(DomainError):
    status_code: int = 429


class ServiceUnavailableError(DomainError):
    status_code: int = 503


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail, **exc.extra}
        )
