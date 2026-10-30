"""`make preflight`: can the configured key use every configured Muse model? (D043)

Uses the network, so it is not part of `make check`. It logs model ids and
variable names only, never the key or any other environment value.
"""

import logging
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from app.agent.llm.muse import MuseClient
from app.agent.llm.ports import LLMUnavailableError
from app.settings import Settings

logger = logging.getLogger("preflight")


class ModelLister(Protocol):
    def available_models(self) -> frozenset[str]: ...


@dataclass(frozen=True)
class ModelCheck:
    variable: str
    model_id: str | None
    available: bool


def configured_models(settings: Settings) -> dict[str, str | None]:
    return {
        "MUSE_AGENT_MODEL": settings.muse_agent_model,
        "MUSE_SEGMENTATION_MODEL": settings.muse_segmentation_model,
        "MUSE_TRANSCRIBE_MODEL": settings.muse_transcribe_model,
    }


def check_models(
    wanted: Mapping[str, str | None], available: frozenset[str]
) -> tuple[ModelCheck, ...]:
    """An unset variable fails, the same as an id the key cannot use."""
    return tuple(
        ModelCheck(variable, model_id, model_id is not None and model_id in available)
        for variable, model_id in wanted.items()
    )


def run_preflight(
    settings: Settings, make_client: Callable[[Settings], ModelLister] = MuseClient.from_settings
) -> bool:
    if settings.muse_api_key is None or not settings.muse_agent_model:
        logger.error("MUSE_API_KEY and MUSE_AGENT_MODEL must be set in .env.")
        return False
    try:
        available = make_client(settings).available_models()
    except LLMUnavailableError as exc:
        logger.error("Model API unreachable: %s. Check MUSE_API_KEY in .env.", exc)
        return False
    checks = check_models(configured_models(settings), available)
    for check in checks:
        state = "OK" if check.available else "MISSING"
        logger.info("%-8s %s = %s", state, check.variable, check.model_id or "(not set)")
    return all(check.available for check in checks)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(0 if run_preflight(Settings()) else 1)


if __name__ == "__main__":
    main()
