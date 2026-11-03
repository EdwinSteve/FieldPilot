"""The farmer asks by voice: transcribe, then answer as in the text chat (D053, D061)."""

from dataclasses import dataclass

from app.agent.loop import AgentRun
from app.services.chat import ChatService
from app.voice.speech import NothingHeardError, SpeechToText


@dataclass(frozen=True)
class VoiceAnswer:
    transcript: str  # shown to the farmer, so they see what was understood
    run: AgentRun


class VoiceChatService:
    def __init__(self, chat: ChatService, speech: SpeechToText, language: str = "en") -> None:
        self._chat = chat
        self._speech = speech
        self._language = language  # the farmer speaks APP_LANGUAGE (D084)

    def ask(self, plot_id: int, audio: bytes) -> VoiceAnswer:
        """Raises NothingHeardError on silence: the model is never asked an empty question."""
        transcript = self._speech.transcribe(audio, self._language)
        if not transcript:
            raise NothingHeardError("the recording has no speech")
        return VoiceAnswer(transcript, self._chat.ask(plot_id, transcript))
