"""The agent: the daily cycle, and the farmer's chat by text or voice (D044, D053, D063, D066)."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from app.agent.loop import AgentRun, RunStatus
from app.api.auth import FarmerDep
from app.api.deps import ContainerDep
from app.api.errors import ChatUnavailableError
from app.api.schemas import ChatIn, ChatOut, DailyCycleIn, DailyCycleOut, VoiceOut

router = APIRouter(prefix="/agent", tags=["agent"])
MAX_AUDIO_BYTES = 32 * 1024 * 1024  # the transcription service's own limit


@router.post("/daily-cycle")
def daily_cycle(body: DailyCycleIn, farmer: FarmerDep, container: ContainerDep) -> DailyCycleOut:
    container.access.require_farm(farmer, body.plot_id)  # the plot comes in the body
    return DailyCycleOut.of(container.daily_cycle(body.plot_id).run(body.plot_id))


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, farmer: FarmerDep, container: ContainerDep) -> ChatOut | JSONResponse:
    container.access.require_farm(farmer, body.plot_id)
    if container.chat is None:
        raise ChatUnavailableError
    run = container.chat.ask(body.plot_id, body.question)
    return _paused_or(run, ChatOut.of(run), container)


@router.post("/chat/voice", response_model=VoiceOut)
def chat_voice(
    plot_id: Annotated[int, Query()],
    audio: Annotated[bytes, Body(media_type="audio/wav")],
    container: ContainerDep,
) -> VoiceOut | JSONResponse:
    """The WAV is the raw request body (Content-Type: audio/wav), D066."""
    if container.voice is None:
        raise ChatUnavailableError
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="The audio is larger than 32 MB.")
    answer = container.voice.ask(plot_id, audio)
    out = VoiceOut(**ChatOut.of(answer.run).model_dump(), transcript=answer.transcript)
    return _paused_or(answer.run, out, container)


def _paused_or[Out: ChatOut](
    run: AgentRun, out: Out, container: ContainerDep
) -> Out | JSONResponse:
    """A paused run means the model did not answer: 503, with the run for the trace."""
    if run.status is RunStatus.PAUSED:
        return JSONResponse(
            status_code=503,
            content={
                "error": "LLMUnavailableError",
                "message": container.config.messages.unavailable["llm_unavailable"],
                "run_id": run.run_id,
            },
        )
    return out
