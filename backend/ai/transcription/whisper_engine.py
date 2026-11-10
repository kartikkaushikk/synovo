from __future__ import annotations
from dataclasses import dataclass
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: list[dict]
    avg_logprob: float
    no_speech_prob: float


class WhisperEngine:
    """
    Singleton-style Faster-Whisper wrapper.
    Handles model loading, chunked transcription, and word-level timestamps.
    """
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info(
                "whisper_loading",
                model=settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
            self._model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                num_workers=2,
            )
            logger.info("whisper_loaded")

    def transcribe(self, audio_path: str) -> list[dict]:
        """
        Transcribe audio file, returning segment dicts with word timestamps.
        Uses VAD filter to skip silence, reducing hallucination.
        """
        self._load_model()
        segments, info = self._model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"threshold": 0.5, "min_silence_duration_ms": 500},
            language=None,  # auto-detect
        )
        logger.info(
            "whisper_transcribed",
            detected_language=info.language,
            duration=info.duration,
        )
        return [
            {
                "text": seg.text.strip(),
                "start": seg.start,
                "end": seg.end,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end, "prob": w.probability}
                    for w in (seg.words or [])
                ],
                "avg_logprob": seg.avg_logprob,
                "no_speech_prob": seg.no_speech_prob,
            }
            for seg in segments
            if seg.text.strip()
        ]
