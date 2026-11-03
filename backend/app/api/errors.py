"""Every error-to-status mapping in one place (§7).

A 5xx body carries a fixed message: never an exception text, a key or a
request body.
"""

from collections.abc import Awaitable, Callable
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent.llm.ports import FixtureExhaustedError, LLMUnavailableError
from app.domain.errors import (
    ActiveCycleExistsError,
    InvalidHarvestError,
    InvalidSowingDateError,
    InvalidTransitionError,
    MissingDataError,
    NotFoundError,
    OpenTasksError,
    OwnRiskRequiredError,
    ScenarioRejectedError,
    SiteJobPendingError,
    UnsupportedActionError,
)
from app.identity.errors import (
    AccountLockedError,
    ConsentRequiredError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidPhoneError,
    InvalidSessionError,
    PhoneTakenError,
    StalePolicyError,
    WeakPasswordError,
)
from app.services.revert import RevertRefusedError
from app.voice.speech import NothingHeardError, SpeechUnavailableError, UnsupportedAudioError

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]


class ChatUnavailableError(Exception):
    """The chat is off under MOCK_LLM=1 (D063)."""


# 4xx: the message explains what to fix, and comes from our own code.
_CLIENT_ERRORS: dict[type[Exception], HTTPStatus] = {
    InvalidCredentialsError: HTTPStatus.UNAUTHORIZED,
    InvalidSessionError: HTTPStatus.UNAUTHORIZED,
    ForbiddenError: HTTPStatus.FORBIDDEN,
    PhoneTakenError: HTTPStatus.CONFLICT,
    StalePolicyError: HTTPStatus.CONFLICT,
    AccountLockedError: HTTPStatus.LOCKED,
    InvalidPhoneError: HTTPStatus.UNPROCESSABLE_ENTITY,
    WeakPasswordError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ConsentRequiredError: HTTPStatus.UNPROCESSABLE_ENTITY,
    NotFoundError: HTTPStatus.NOT_FOUND,
    ActiveCycleExistsError: HTTPStatus.CONFLICT,
    OpenTasksError: HTTPStatus.CONFLICT,
    SiteJobPendingError: HTTPStatus.CONFLICT,
    InvalidSowingDateError: HTTPStatus.UNPROCESSABLE_ENTITY,
    OwnRiskRequiredError: HTTPStatus.UNPROCESSABLE_ENTITY,
    InvalidHarvestError: HTTPStatus.UNPROCESSABLE_ENTITY,
    InvalidTransitionError: HTTPStatus.CONFLICT,
    RevertRefusedError: HTTPStatus.CONFLICT,
    MissingDataError: HTTPStatus.CONFLICT,
    UnsupportedActionError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ScenarioRejectedError: HTTPStatus.UNPROCESSABLE_ENTITY,
    UnsupportedAudioError: HTTPStatus.UNPROCESSABLE_ENTITY,
    NothingHeardError: HTTPStatus.UNPROCESSABLE_ENTITY,
}

# 5xx: a fixed, safe message per error.
_UNAVAILABLE: dict[type[Exception], str] = {
    LLMUnavailableError: "El modelo no respondió. Intenta de nuevo en un momento.",
    SpeechUnavailableError: "El servicio de transcripción no respondió.",
    ChatUnavailableError: "El chat necesita MOCK_LLM=0 y una clave de API.",
    FixtureExhaustedError: "La respuesta grabada no corresponde a esta granja (MOCK_LLM=1).",
}


def install_error_handlers(app: FastAPI) -> None:
    for error, status in _CLIENT_ERRORS.items():
        app.add_exception_handler(error, _client_handler(status))
    for error, message in _UNAVAILABLE.items():
        app.add_exception_handler(error, _unavailable_handler(message))


def _client_handler(status: HTTPStatus) -> Handler:
    # RFC 6750: a 401 tells the client which scheme to use.
    headers = {"WWW-Authenticate": "Bearer"} if status is HTTPStatus.UNAUTHORIZED else None

    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "message": str(exc)},
            headers=headers,
        )

    return handler


def _unavailable_handler(message: str) -> Handler:
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            content={"error": type(exc).__name__, "message": message},
        )

    return handler
