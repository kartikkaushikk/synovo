"""
Pyannote speaker diarization engine.
Runs pyannote.audio pipeline in a thread-pool to avoid blocking the Celery worker.

Model: pyannote/speaker-diarization-3.1
Requires HuggingFace token with model access accepted at:
  https://huggingface.co/pyannote/speaker-diarization-3.1
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import ClassVar

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DiarizationSegment:
    speaker: str
    start: float
    end: float

    def to_dict(self) -> dict:
        return {"speaker": self.speaker, "start": self.start, "end": self.end}


class DiarizationEngine:
    """
    Thread-safe singleton wrapping pyannote pipeline.
    Lazy-loaded on first call to keep worker startup fast.
    """

    _instance: ClassVar["DiarizationEngine | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._pipeline = None

    @classmethod
    def get(cls) -> "DiarizationEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from pyannote.audio import Pipeline
            import torch

            logger.info("diarization_loading_model")
            if not settings.HUGGINGFACE_TOKEN or settings.HUGGINGFACE_TOKEN == "hf_your_token_here":
                raise RuntimeError("HUGGINGFACE_TOKEN is missing; diarization disabled")
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=settings.HUGGINGFACE_TOKEN,
            )
            if self._pipeline is None:
                raise RuntimeError("Failed to load diarization pipeline (got None)")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._pipeline.to(torch.device(device))
            logger.info("diarization_model_loaded", device=device)
        except Exception as exc:
            logger.error("diarization_model_load_failed", error=str(exc))
            raise

    def diarize(self, audio_path: str, num_speakers: int | None = None) -> list[dict]:
        """
        Run diarization on a local audio file.
        Returns list of {speaker, start, end} dicts serialisable for Celery.

        Args:
            audio_path: Path to local audio file (wav/mp3/etc.)
            num_speakers: Hint for number of speakers. If None, auto-detected.
        """
        self._load_pipeline()

        kwargs: dict = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers

        logger.info("diarization_started", path=audio_path)
        diarization = self._pipeline(audio_path, **kwargs)

        segments: list[dict] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                DiarizationSegment(
                    speaker=speaker,
                    start=round(turn.start, 3),
                    end=round(turn.end, 3),
                ).to_dict()
            )

        logger.info("diarization_done", segments=len(segments), path=audio_path)
        return segments
