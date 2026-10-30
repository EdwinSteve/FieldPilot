"""The agent over HTTP: chat, voice and the daily cycle (D053, D061, D063, D066)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.llm.mock import MockLLMClient
from app.agent.messages import LLMResponse, ToolCall
from app.voice.speech import MockSpeechToText
from tests.fakes import FlakyLLM
from tests.integration.api.conftest import Farm, with_chat, with_cycle
from tests.unit.voice.wavs import make_wav

ANSWER = LLMResponse(
    None, ToolCall("c1", "answer_farmer", '{"text_es": "Lo decide el ciclo diario.", "cited": []}')
)
WAV = {"Content-Type": "audio/wav"}


def test_mock_mode_chat_is_503_and_says_why(client: TestClient, farm: Farm) -> None:
    """D063: never a canned answer that looks real."""
    text = client.post("/agent/chat", json={"plot_id": farm.plot_id, "question": "¿Riego?"})
    voice = client.post(
        "/agent/chat/voice", params={"plot_id": farm.plot_id}, content=make_wav(), headers=WAV
    )

    for response in (text, voice):
        assert response.status_code == 503
        assert response.json()["message"] == "El chat necesita MOCK_LLM=0 y una clave de API."


def test_the_chat_returns_the_verified_answer(app: FastAPI, client: TestClient, farm: Farm) -> None:
    with_chat(app, MockLLMClient([ANSWER]))

    response = client.post("/agent/chat", json={"plot_id": farm.plot_id, "question": "¿Riego?"})

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["answer"], body["turns"]) == (
        "completed",
        "Lo decide el ciclo diario.",
        1,
    )


def test_an_unavailable_model_is_503_with_the_run_id(
    app: FastAPI, client: TestClient, farm: Farm
) -> None:
    with_chat(app, FlakyLLM(MockLLMClient([]), failing_attempts=[1]))

    response = client.post("/agent/chat", json={"plot_id": farm.plot_id, "question": "¿Riego?"})

    assert response.status_code == 503
    assert response.json()["error"] == "LLMUnavailableError"
    assert response.json()["run_id"].endswith("-orchestrator")


def test_an_empty_question_is_422(client: TestClient, farm: Farm) -> None:
    assert (
        client.post("/agent/chat", json={"plot_id": farm.plot_id, "question": ""}).status_code
        == 422
    )


def test_voice_returns_what_was_understood(app: FastAPI, client: TestClient, farm: Farm) -> None:
    speech = MockSpeechToText("¿Necesita agua la zona dos?")
    with_chat(app, MockLLMClient([ANSWER]), speech)
    audio = make_wav()

    response = client.post(
        "/agent/chat/voice", params={"plot_id": farm.plot_id}, content=audio, headers=WAV
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "¿Necesita agua la zona dos?"
    assert response.json()["answer"] == "Lo decide el ciclo diario."
    assert speech.calls == [(audio, "es")]


def test_unsupported_audio_or_silence_is_422(app: FastAPI, client: TestClient, farm: Farm) -> None:
    with_chat(app, MockLLMClient([]), MockSpeechToText(""))

    silence = client.post(
        "/agent/chat/voice", params={"plot_id": farm.plot_id}, content=make_wav(), headers=WAV
    )

    assert silence.status_code == 422 and silence.json()["error"] == "NothingHeardError"


def test_a_mock_cycle_that_does_not_match_the_farm_is_503(
    app: FastAPI, client: TestClient, farm: Farm
) -> None:
    """A replay that runs out before the cycle ends: the API says so instead of a 500."""
    with_cycle(app, MockLLMClient([]))

    response = client.post("/agent/daily-cycle", json={"plot_id": farm.plot_id})

    assert response.status_code == 503
    assert response.json() == {
        "error": "FixtureExhaustedError",
        "message": "La respuesta grabada no corresponde a esta granja (MOCK_LLM=1).",
    }


def test_a_paused_daily_cycle_reports_where_it_stopped(
    app: FastAPI, client: TestClient, farm: Farm
) -> None:
    with_cycle(app, FlakyLLM(MockLLMClient([]), failing_attempts=[1]))

    body = client.post("/agent/daily-cycle", json={"plot_id": farm.plot_id}).json()

    assert (body["status"], body["stopped_at"]) == ("paused", "monitoring")
    assert [r["subagent"] for r in body["runs"]] == ["monitoring"]
    assert body["brief"]["plot_id"] == farm.plot_id
