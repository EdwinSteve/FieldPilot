from pathlib import Path

import pytest

from app.domain.errors import ConfigError
from app.satellite.config import load_imaging_config
from tests.conftest import CONFIG_DIR


def test_the_shipped_config() -> None:
    config = load_imaging_config(CONFIG_DIR / "imaging.yaml")

    assert config.segmentation_prompt == "brown patch"


@pytest.mark.parametrize(
    "text",
    [
        "segmentation_prompt: ''\n",
        "{}\n",
        "segmentation_prompt: x\nextra: 1\n",
        # D077: the threshold is per crop now; a global one is refused, not ignored.
        "low_ndvi_threshold: 0.4\nsegmentation_prompt: brown patch\n",
    ],
)
def test_an_unsafe_config_stops_startup(tmp_path: Path, text: str) -> None:
    path = tmp_path / "imaging.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match=r"imaging\.yaml"):
        load_imaging_config(path)
