"""FastAPI application factory. Wiring only; no business logic."""

from fastapi import FastAPI

from app.api.routes import health
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Run with: `uvicorn app.main:create_app --factory`.
    """
    resolved_settings = settings or Settings()
    app = FastAPI(title="FieldPilot", version="0.1.0")
    app.state.settings = resolved_settings
    app.include_router(health.router)
    return app
