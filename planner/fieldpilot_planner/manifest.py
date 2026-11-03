"""File digests for the bundle manifest, the same on Windows and Linux (no torch).

A text file can reach a machine with CRLF or LF line endings depending on git
and the platform that wrote it. Its digest is taken over LF endings, so a
bundle trained on Windows verifies on Linux. Binary files are hashed as they are.
"""

import hashlib
from collections.abc import Mapping
from pathlib import Path

TEXT_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".md", ".csv", ".txt"})


def file_digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def changed_files(directory: Path, expected: Mapping[str, str]) -> list[str]:
    """The files of `expected` whose digest differs, or that are missing."""
    return [
        name
        for name, digest in expected.items()
        if not (directory / name).is_file() or file_digest(directory / name) != digest
    ]
