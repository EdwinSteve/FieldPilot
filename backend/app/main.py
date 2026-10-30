"""FastAPI application factory. Wiring only; no business logic."""

from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.routes import agent, control, farm, health, log, tasks
from app.bootstrap import load_runtime_config, resolve_revert_window, start_runtime
from app.container import build_container
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
    app.state.container = build_container(resolved_settings, runtime_config, runtime)
    for module in (health, farm, tasks, log, agent, control):
        app.include_router(module.router)
    install_error_handlers(app)
    return app
