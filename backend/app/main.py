"""FastAPI application factory. Wiring only; no business logic."""

from fastapi import Depends, FastAPI

from app.api.auth import require_farm_access
from app.api.errors import install_error_handlers
from app.api.routes import agent, autonomy, control, farm, health, lifecycle, log, tasks, trace
from app.api.routes import auth as auth_routes
from app.bootstrap import (
    load_runtime_config,
    resolve_auth,
    resolve_revert_window,
    start_runtime,
)
from app.container import build_container
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Run with: `uvicorn app.main:create_app --factory`.
    Raises ConfigError, and so refuses to start, on any unsafe configuration.
    Startup reconciliation runs after that and before any request (D013).
    """
    resolved_settings = settings or Settings()
    runtime_config = load_runtime_config(
        resolved_settings.config_dir, resolved_settings.app_language
    )
    revert_window = resolve_revert_window(resolved_settings, runtime_config.policy)
    auth = resolve_auth(resolved_settings)
    runtime = start_runtime(resolved_settings, runtime_config, revert_window)
    app = FastAPI(title="FieldPilot", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.config = runtime_config
    app.state.runtime = runtime
    app.state.container = build_container(resolved_settings, runtime_config, runtime, auth)
    for module in (health, auth_routes, trace):  # trace: the public passport
        app.include_router(module.router)
    for module in (farm, lifecycle, tasks, log, agent, autonomy, control):  # D082: farm roles only
        app.include_router(module.router, dependencies=[Depends(require_farm_access)])
    install_error_handlers(app, runtime_config.messages)
    return app
