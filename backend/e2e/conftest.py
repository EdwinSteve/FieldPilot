"""The end-to-end harness: the real backend, and the Muse it talks to (D090).

Black box: the tests reach FieldPilot only over HTTP, as the frontend does,
with real tokens and a fresh SQLite file. The backend runs with MOCK_LLM=0, so
every agent turn goes through the OpenAI SDK. Two modes:

- **fake** (`make e2e`, the default and CI): the fake Muse (e2e/fake_muse) plays
  the agents on localhost, with a placeholder key. Deterministic, no network.
- **live** (`make e2e-live`, E2E_MUSE=live): the real Meta Model API, with the
  key and model ids of the developer's .env. It tests the model's behaviour,
  costs quota and never runs in CI. The backend reads the key from .env, as in
  any run; this file only checks that it is set and never prints it.
"""

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx2
import pytest

from app.settings import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
STARTUP_SECONDS = 60
PASSWORD = "cafe-con-panela"
LIVE = os.environ.get("E2E_MUSE", "fake") == "live"
REQUEST_SECONDS = 600 if LIVE else 60  # a live daily cycle is many model turns
MUSE_SETTINGS = ("MUSE_API_KEY", "MUSE_API_BASE_URL", "MUSE_AGENT_MODEL",
                 "MUSE_SEGMENTATION_MODEL", "MUSE_TRANSCRIBE_MODEL")  # fmt: skip


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def _serve(target: str, port: int, env: dict[str, str], log: Path) -> subprocess.Popen[bytes]:
    command = [sys.executable, "-m", "uvicorn", target, "--port", str(port), "--log-level",
               "warning"]  # fmt: skip
    if target.endswith("create_app"):
        command.append("--factory")
    with log.open("wb") as out:
        return subprocess.Popen(command, cwd=BACKEND_DIR, env=env, stdout=out, stderr=out)


def _wait(url: str, process: subprocess.Popen[bytes], log: Path) -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{url} exited at startup:\n{log.read_text()[-3000:]}")
        try:
            if httpx2.get(url, timeout=2).status_code < 500:
                return
        except httpx2.TransportError:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"{url} did not start in {STARTUP_SECONDS} s:\n{log.read_text()[-3000:]}")


def _backend_env(database: Path, muse_url: str | None) -> dict[str, str]:
    """Explicit values for everything that matters, so a developer's .env cannot leak in.

    Live (`muse_url` None), the Muse settings are left out, so the backend reads the
    key and the model ids from .env, as `make dev` does.
    """
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{database}",
        "APP_PROFILE": "demo",  # the sensor kit and the stand-ins of D089
        "APP_LANGUAGE": "en",
        "AUTH_REQUIRED": "1",  # real tokens for every role
        "AUTH_JWT_SECRET": "e2e-" + "k" * 44,
        "MOCK_LLM": "0",  # every agent turn goes through the OpenAI SDK
        "PLANNER_SITE_BUILDER": "off",  # the shipped site fixture, no satellite download
    }
    for name in MUSE_SETTINGS:
        env.pop(name, None)
    if muse_url is not None:
        env |= {
            "MUSE_API_KEY": "e2e-placeholder-not-a-key",
            "MUSE_API_BASE_URL": f"{muse_url}/v1",
            "MUSE_AGENT_MODEL": "muse-spark-1.3",
            "MUSE_SEGMENTATION_MODEL": "sam-3.1",
            "MUSE_TRANSCRIBE_MODEL": "muse-voice-transcribe-1.0",
        }
    return env


def _require_live_settings() -> None:
    """Stop before starting anything, naming what is missing, never a value."""
    settings = Settings(mock_llm=True)  # only to read .env; the backend runs with 0
    found = {
        "MUSE_API_KEY": settings.muse_api_key is not None,
        "MUSE_AGENT_MODEL": bool(settings.muse_agent_model),
        "MUSE_SEGMENTATION_MODEL": bool(settings.muse_segmentation_model),
    }
    missing = [name for name, present in found.items() if not present]
    if missing:
        pytest.exit(f"make e2e-live needs {', '.join(missing)} in .env", returncode=2)


@dataclass
class Stack:
    api: httpx2.Client
    muse: httpx2.Client | None  # None live: the real Muse keeps no log for us
    env: dict[str, str]

    @property
    def live(self) -> bool:
        return self.muse is None

    def muse_log(self) -> list[dict[str, Any]]:
        """Every turn the fake Muse played (fake mode only)."""
        assert self.muse is not None, "the real Muse keeps no log"
        log: list[dict[str, Any]] = self.muse.get("/_e2e/log").json()
        return log

    def create_account(self, phone: str, name: str, role: str) -> None:
        """An operator or admin, as `make user` creates one: there is no public route.

        The script asks with `getpass`, which reads the terminal, not stdin, when there
        is one. A new session has no terminal, so it reads the answers piped here.
        """
        answers = f"y\n{PASSWORD}\n{PASSWORD}\n"
        result = subprocess.run(
            [sys.executable, "scripts/create_user.py", "--phone", phone, "--name", name,
             "--role", role],
            cwd=BACKEND_DIR, env=self.env, input=answers.encode(), capture_output=True,
            timeout=60, check=False, start_new_session=True,
        )  # fmt: skip
        assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()


@pytest.fixture(scope="session")
def stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stack]:
    if LIVE:
        _require_live_settings()
    workdir = tmp_path_factory.mktemp("e2e")
    muse_port, api_port = _free_port(), _free_port()
    muse_url, api_url = f"http://127.0.0.1:{muse_port}", f"http://127.0.0.1:{api_port}"
    muse_log, api_log = workdir / "muse.log", workdir / "backend.log"
    muse = None
    if not LIVE:
        muse = _serve("e2e.fake_muse.app:app", muse_port, dict(os.environ), muse_log)
    env = _backend_env(workdir / "fieldpilot.db", None if LIVE else muse_url)
    backend = None
    try:
        if muse is not None:
            _wait(f"{muse_url}/v1/models", muse, muse_log)
        backend = _serve("app.main:create_app", api_port, env, api_log)
        _wait(f"{api_url}/health", backend, api_log)
        with httpx2.Client(base_url=api_url, timeout=REQUEST_SECONDS) as api:
            if muse is None:
                yield Stack(api, None, env)
            else:
                with httpx2.Client(base_url=muse_url, timeout=10) as muse_client:
                    yield Stack(api, muse_client, env)
    finally:
        for process in (backend, muse):
            if process is not None:
                process.terminate()
                process.wait(timeout=10)
