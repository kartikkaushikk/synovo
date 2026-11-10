from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ai.diarization.pyannote_engine import DiarizationEngine


def test_load_pipeline_keeps_pyannote_instance_when_to_returns_none():
    engine = DiarizationEngine()
    pipeline = MagicMock()
    pipeline.to.return_value = None
    pipeline_cls = SimpleNamespace(from_pretrained=MagicMock(return_value=pipeline))
    pyannote_audio = SimpleNamespace(Pipeline=pipeline_cls)
    torch_module = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        device=lambda name: name,
    )

    with (
        patch("ai.diarization.pyannote_engine.settings.HUGGINGFACE_TOKEN", "hf_test_token"),
        patch.dict(
            "sys.modules",
            {"pyannote.audio": pyannote_audio, "torch": torch_module},
        ),
    ):
        engine._load_pipeline()

    assert engine._pipeline is pipeline
    pipeline.to.assert_called_once()


def test_diarization_task_converts_download_to_wav():
    from workers.tasks.diarization import diarization_task

    async def fake_download_file(_file_url):
        return b"audio-bytes"

    engine = MagicMock()
    engine.diarize.return_value = [{"speaker": "SPEAKER_00", "start": 0, "end": 1}]

    with (
        patch("app.core.config.settings.HUGGINGFACE_TOKEN", "hf_test_token"),
        patch("app.core.config.settings.ENABLE_CPU_DIARIZATION", True),
        patch("workers.tasks.diarization.set_job_status"),
        patch("app.services.storage.download_file", side_effect=fake_download_file),
        patch("workers.tasks.diarization.subprocess.run") as run_ffmpeg,
        patch("ai.diarization.pyannote_engine.DiarizationEngine.get", return_value=engine),
    ):
        segments = diarization_task.run("job-1", "https://example.com/audio.webm")

    assert segments == [{"speaker": "SPEAKER_00", "start": 0, "end": 1}]
    run_ffmpeg.assert_called_once()
    ffmpeg_args = run_ffmpeg.call_args.args[0]
    assert ffmpeg_args[:5] == ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    assert ffmpeg_args[-1].endswith(".wav")
    engine.diarize.assert_called_once()
    assert engine.diarize.call_args.args[0].endswith(".wav")
