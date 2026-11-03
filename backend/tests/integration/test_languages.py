"""English by default, Spanish kept (D084): both catalogues complete, every error translated."""

import re
from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient

from app.autonomy.messages import load_message_catalog
from app.main import create_app
from app.planning.site_jobs import SITE_MESSAGES
from app.settings import REPO_ROOT, Settings

MESSAGES = REPO_ROOT / "config" / "messages"
APP = REPO_ROOT / "backend" / "app"


def test_both_catalogues_have_the_same_keys() -> None:
    en = load_message_catalog(MESSAGES / "en.yaml")
    es = load_message_catalog(MESSAGES / "es.yaml")
    assert (en.language, en.decimal_separator) == ("en", ".")
    assert (es.language, es.decimal_separator) == ("es", ",")
    for section in ("rules", "inputs", "labels", "agent_texts", "crops", "unavailable"):
        assert set(getattr(en, section)) == set(getattr(es, section)), section


def test_every_error_key_raised_in_the_code_has_spanish() -> None:
    """English is written at the raise site; Spanish must exist for every key."""
    keys = {
        match
        for path in APP.rglob("*.py")
        for match in re.findall(r'key="([a-z_]+)"', path.read_text(encoding="utf-8"))
    }
    keys |= set(SITE_MESSAGES) | {"not_found"}
    spanish = load_message_catalog(MESSAGES / "es.yaml").errors
    assert keys, "no keys found: the scan is broken"
    assert sorted(keys - set(spanish)) == []


@pytest.mark.parametrize(
    ("language", "message"),
    [("en", "Lot FP-9-20260101-1 not found"), ("es", "No se encontró Lot FP-9-20260101-1.")],
)
def test_the_api_answers_in_app_language(
    tmp_path: Path, language: Literal["en", "es"], message: str
) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'lang.db'}",
        mock_llm=True,
        app_language=language,
        planner_site_builder="off",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/trace/FP-9-20260101-1")
    assert response.json()["message"] == message


def test_numbers_follow_the_language() -> None:
    assert load_message_catalog(MESSAGES / "en.yaml").number(20.5) == "20.5"
    assert load_message_catalog(MESSAGES / "es.yaml").number(20.5) == "20,5"
