"""Bundle digests verify on any platform (a bundle trained on Windows serves on Linux)."""

import json
from pathlib import Path

from fieldpilot_planner.manifest import changed_files, file_digest


def test_text_digests_ignore_crlf_but_binary_digests_do_not(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_bytes(b'{"x": 1}\r\n')
    (tmp_path / "b.json").write_bytes(b'{"x": 1}\n')
    (tmp_path / "a.onnx").write_bytes(b"\x08\r\n")
    (tmp_path / "b.onnx").write_bytes(b"\x08\n")

    assert file_digest(tmp_path / "a.json") == file_digest(tmp_path / "b.json")
    assert file_digest(tmp_path / "a.onnx") != file_digest(tmp_path / "b.onnx")


def test_changed_files_names_edited_and_missing_files(tmp_path: Path) -> None:
    (tmp_path / "metrics.json").write_text('{"adopted": true}\n', encoding="utf-8")
    expected = {"metrics.json": file_digest(tmp_path / "metrics.json"), "model.onnx": "0" * 64}
    assert changed_files(tmp_path, expected) == ["model.onnx"]

    (tmp_path / "metrics.json").write_text('{"adopted": false}\n', encoding="utf-8")
    assert changed_files(tmp_path, expected) == ["metrics.json", "model.onnx"]


def test_the_committed_bundles_verify_here() -> None:
    models = Path(__file__).resolve().parents[1] / "models"
    for manifest in models.glob("*/manifest.json"):
        files = json.loads(manifest.read_text(encoding="utf-8"))["files"]
        assert changed_files(manifest.parent, files) == [], manifest.parent.name
