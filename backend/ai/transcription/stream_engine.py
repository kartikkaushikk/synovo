import numpy as np
import torch
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Module-level singletons — models are loaded ONCE per process, not per
# WebSocket connection. This is the most critical performance fix.
# ---------------------------------------------------------------------------
_whisper_model: WhisperModel | None = None
_vad_model = None
_vad_available: bool | None = None  # None = not yet attempted


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if torch.cuda.is_available() else "int8"
        _whisper_model = WhisperModel("base", device=device, compute_type=compute_type)
    return _whisper_model


def _get_vad_model():
    """
    Load Silero VAD once. If it fails (network error, missing torchaudio, etc.)
    we set _vad_available = False so every subsequent call skips it gracefully.
    """
    global _vad_model, _vad_available
    if _vad_available is None:
        try:
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
                verbose=False,
            )
            _vad_model = model
            _vad_available = True
        except Exception as exc:
            print(f"[stream_engine] WARNING: Silero VAD failed to load ({exc}). "
                  "Falling back to energy-based VAD.")
            _vad_available = False
    return _vad_model if _vad_available else None


# ---------------------------------------------------------------------------
# Energy-based VAD fallback (no external model required)
# ---------------------------------------------------------------------------
def _energy_is_speech(audio: np.ndarray, threshold: float = 0.01) -> bool:
    """Simple RMS energy gate — fast and always available."""
    rms = np.sqrt(np.mean(audio ** 2))
    return rms > threshold


class StreamTranscriber:
    """
    Stateful, per-session transcription engine.

    Audio pipeline:
      1. Accumulate incoming PCM bytes until we have ≥ min_chunk_s of audio.
      2. Run VAD (Silero if available, energy otherwise) on the chunk.
      3. If speech detected → append to speech_buffer, reset silence counter.
         If silence detected  → increment silence counter.
      4. Transcribe when:
         a) Speech just ended AND silence_chunks >= SILENCE_CHUNKS_TO_TRANSCRIBE
         b) Speech buffer exceeds MAX_SPEECH_S (prevents indefinite buffering)
    """

    SAMPLE_RATE: int = 16_000
    MIN_CHUNK_S: float = 0.5          # seconds of audio per VAD decision
    MAX_SPEECH_S: float = 8.0         # force-transcribe after 8 s of continuous speech
    MIN_TRANSCRIPT_S: float = 0.5     # ignore very short utterances
    VAD_THRESHOLD: float = 0.5        # Silero probability threshold
    SILENCE_CHUNKS_TO_TRANSCRIBE: int = 2  # wait for 2 consecutive silent chunks (= 1 s)

    def __init__(self) -> None:
        self.model = _get_whisper_model()
        self.vad_model = _get_vad_model()   # may be None — that is fine

        self.audio_buffer: bytearray = bytearray()
        self.speech_buffer: list[np.ndarray] = []
        self.is_speaking: bool = False
        self.silence_chunks: int = 0
        self.global_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_chunk(self, pcm_data: bytes) -> dict | None:
        """
        Feed a chunk of 16 kHz, 16-bit, mono PCM audio.

        Returns a result dict when a complete utterance is ready::

            {"text": str, "is_final": bool, "timestamp": float}

        Returns None while still accumulating audio.
        """
        if not pcm_data:
            return None

        # Ensure even number of bytes (16-bit samples)
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]
        if not pcm_data:
            return None

        self.audio_buffer.extend(pcm_data)

        min_bytes = int(self.SAMPLE_RATE * self.MIN_CHUNK_S) * 2
        if len(self.audio_buffer) < min_bytes:
            return None

        # Consume exactly one chunk from the front
        chunk_bytes = bytes(self.audio_buffer[:min_bytes])
        del self.audio_buffer[:min_bytes]

        audio_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
        audio_f32 = audio_int16.astype(np.float32) / 32768.0

        self.global_time += len(audio_f32) / self.SAMPLE_RATE

        is_speech = self._run_vad(audio_f32)

        if is_speech:
            self.is_speaking = True
            self.silence_chunks = 0
            self.speech_buffer.append(audio_f32)

            # Force transcription if buffer is too long (continuous talker)
            if self._speech_buffer_duration() >= self.MAX_SPEECH_S:
                return self._transcribe()

            return None

        else:
            # Silence frame
            self.silence_chunks += 1

            if self.is_speaking:
                # Include a bit of trailing silence so the last word isn't cut off
                self.speech_buffer.append(audio_f32)

                if self.silence_chunks >= self.SILENCE_CHUNKS_TO_TRANSCRIBE:
                    return self._transcribe()

            return None

    def cleanup(self) -> None:
        self.speech_buffer.clear()
        self.audio_buffer.clear()
        self.is_speaking = False
        self.silence_chunks = 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_vad(self, audio: np.ndarray) -> bool:
        """Return True if this chunk contains speech."""
        if self.vad_model is not None:
            try:
                tensor = torch.from_numpy(audio)
                prob: float = self.vad_model(tensor, self.SAMPLE_RATE).item()
                return prob > self.VAD_THRESHOLD
            except Exception:
                pass  # fall through to energy VAD

        return _energy_is_speech(audio)

    def _speech_buffer_duration(self) -> float:
        total = sum(len(a) for a in self.speech_buffer)
        return total / self.SAMPLE_RATE

    def _transcribe(self) -> dict | None:
        """Concatenate the speech buffer and run Whisper. Resets state."""
        if not self.speech_buffer:
            return None

        full_audio = np.concatenate(self.speech_buffer)
        self.speech_buffer = []
        self.is_speaking = False
        self.silence_chunks = 0

        if len(full_audio) / self.SAMPLE_RATE < self.MIN_TRANSCRIPT_S:
            return None

        try:
            segments, _ = self.model.transcribe(
                full_audio,
                beam_size=1,
                vad_filter=False,   # We already did VAD ourselves
                language=None,      # auto-detect
            )
            text = " ".join(s.text for s in segments).strip()
            if text:
                return {
                    "text": text,
                    "is_final": True,
                    "timestamp": round(self.global_time, 2),
                }
        except Exception as exc:
            print(f"[stream_engine] Transcription error: {exc}")

        return None
