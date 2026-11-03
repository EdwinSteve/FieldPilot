"""Every error-to-status mapping in one place (§7).

A 5xx body carries a fixed message: never an exception text, a key or a
request body.
"""

from collections.abc import Awaitable, Callable
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent.llm.ports import FixtureExhaustedError, LLMUnavailableError
from app.autonomy.messages import MessageCatalog
from app.domain.errors import (
    ActiveCycleExistsError,
    DomainError,
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
from app.market.errors import (
    EmptyCartError,
    InvalidOfferError,
    InvalidReceiptError,
    ListingStateError,
    OutOfStockError,
    PaymentDeclinedError,
    PriceTooLowError,
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
    ListingStateError: HTTPStatus.CONFLICT,
    OutOfStockError: HTTPStatus.CONFLICT,
    EmptyCartError: HTTPStatus.CONFLICT,
    PriceTooLowError: HTTPStatus.UNPROCESSABLE_ENTITY,
    InvalidOfferError: HTTPStatus.UNPROCESSABLE_ENTITY,
    InvalidReceiptError: HTTPStatus.UNPROCESSABLE_ENTITY,
    PaymentDeclinedError: HTTPStatus.PAYMENT_REQUIRED,
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

# 5xx: a fixed, safe message per error, from the catalogue's `unavailable` section.
_UNAVAILABLE: dict[type[Exception], str] = {
    LLMUnavailableError: "llm_unavailable",
    SpeechUnavailableError: "speech_unavailable",
    ChatUnavailableError: "chat_unavailable",
    FixtureExhaustedError: "fixture_exhausted",
}


def install_error_handlers(app: FastAPI, messages: MessageCatalog) -> None:
    """Every message the client sees is in the catalogue's language (D084)."""
    for error, status in _CLIENT_ERRORS.items():
        app.add_exception_handler(error, _client_handler(status, messages))
    for error, key in _UNAVAILABLE.items():
        app.add_exception_handler(error, _unavailable_handler(messages.unavailable[key]))


def _client_handler(status: HTTPStatus, messages: MessageCatalog) -> Handler:
    # RFC 6750: a 401 tells the client which scheme to use.
    headers = {"WWW-Authenticate": "Bearer"} if status is HTTPStatus.UNAUTHORIZED else None

    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "message": _message(exc, messages)},
            headers=headers,
        )

    return handler


def _message(exc: Exception, messages: MessageCatalog) -> str:
    """The catalogue's text for the error's key; the code's English text otherwise."""
    if isinstance(exc, DomainError) and exc.key is not None:
        return messages.error(exc.key, exc.params, str(exc))
    return str(exc)


def _unavailable_handler(message: str) -> Handler:
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            content={"error": type(exc).__name__, "message": message},
        )

    return handler
