from pathlib import Path

import pytest

from app.actuation.config import load_actuation_config
from app.domain.errors import ConfigError
from tests.conftest import CONFIG_DIR


def test_shipped_rate_is_six_mm_per_hour() -> None:
    assert load_actuation_config(CONFIG_DIR / "actuation.yaml").irrigation_rate_mm_per_h == 6.0


@pytest.mark.parametrize(
    "content",
    ["irrigation_rate_mm_per_h: 0\n", "irrigation_rate_mm_per_h: -1\n", "{}\n", "rate: 6\n"],
)
def test_invalid_file_refuses_to_load(tmp_path: Path, content: str) -> None:
    path = tmp_path / "actuation.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError, match=r"actuation\.yaml"):
        load_actuation_config(path)


def test_missing_file_refuses_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_actuation_config(tmp_path / "actuation.yaml")
