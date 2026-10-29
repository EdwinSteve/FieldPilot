"""FastAPI application factory. Wiring only; no business logic."""

from fastapi import FastAPI

from app.api.routes import health
from app.bootstrap import load_runtime_config, resolve_revert_window, start_runtime
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Run with: `uvicorn app.main:create_app --factory`.
    Raises ConfigError, and so refuses to start, on any unsafe configuration.
    Startup reconciliation runs after that and before any request (D013).
    """
    resolved_settings = settings or Settings()
    runtime_config = load_runtime_config(resolved_settings.config_dir)
    revert_window = resolve_revert_window(resolved_settings, runtime_config.policy)
    runtime = start_runtime(resolved_settings, runtime_config, revert_window)
    app = FastAPI(title="FieldPilot", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.config = runtime_config
    app.state.runtime = runtime
    app.include_router(health.router)
    return app
