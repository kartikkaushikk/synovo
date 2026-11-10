"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Mic, MicOff, Activity, AlertTriangle, Loader2 } from "lucide-react";

type TranscriptItem = { text: string; t: number };
type Status = "idle" | "connecting" | "recording" | "error";

export default function StreamPage() {
  const [status, setStatus] = useState<Status>("idle");
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [micLevel, setMicLevel] = useState(0); // 0–1, for the level meter

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const sessionId = useRef(
    `session_${Math.random().toString(36).substr(2, 9)}`,
  ).current;

  // Clean up everything
  const stopRecording = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.onaudioprocess = null;
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setMicLevel(0);
    setStatus("idle");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopRecording();
  }, [stopRecording]);

  // Mic-level animation loop
  const startLevelMeter = (analyser: AnalyserNode) => {
    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      setMicLevel(Math.min(1, Math.sqrt(sum / data.length) * 6));
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
  };

  // Downsample Float32 buffer from audioContext.sampleRate → 16 kHz
  const downsample = (buf: Float32Array, fromRate: number): Float32Array => {
    if (fromRate === 16000) return buf;
    const ratio = fromRate / 16000;
    const newLen = Math.round(buf.length / ratio);
    const out = new Float32Array(newLen);
    let off = 0;
    for (let i = 0; i < newLen; i++) {
      const next = Math.round((i + 1) * ratio);
      let acc = 0, count = 0;
      for (let j = off; j < next && j < buf.length; j++) { acc += buf[j]; count++; }
      out[i] = count > 0 ? acc / count : 0;
      off = next;
    }
    return out;
  };

  const floatTo16BitPCM = (input: Float32Array): ArrayBuffer => {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out.buffer;
  };

  const startRecording = async () => {
    try {
      setError(null);
      setTranscript([]);
      setStatus("connecting");

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Build WebSocket URL — handle both http and https origins
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const wsUrl = base.replace(/^https/, "wss").replace(/^http/, "ws");
      const ws = new WebSocket(`${wsUrl}/api/v1/ws/stream/${sessionId}`);
      wsRef.current = ws;

      ws.binaryType = "arraybuffer";

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data as string);
        if (data.type === "transcript") {
          setTranscript((prev) => [...prev, { text: data.text, t: data.t }]);
        } else if (data.type === "error") {
          setError(data.message);
          stopRecording();
        }
      };

      ws.onerror = () => {
        setError(
          "WebSocket error — make sure the backend is running at " + base,
        );
        stopRecording();
      };

      ws.onclose = (ev) => {
        if (ev.code !== 1000 && ev.code !== 1005) {
          // Abnormal close — show an error if we were still recording
          setError(`Connection closed unexpectedly (code ${ev.code})`);
        }
        setStatus((s) => (s === "recording" ? "idle" : s));
      };

      ws.onopen = async () => {
        setStatus("recording");

        const audioContext = new AudioContext();
        audioContextRef.current = audioContext;
        await audioContext.resume();

        const source = audioContext.createMediaStreamSource(stream);
        sourceRef.current = source;

        // Analyser for the mic-level meter (no audio output)
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;
        source.connect(analyser);
        startLevelMeter(analyser);

        // ScriptProcessorNode for capturing PCM frames
        // NOTE: We route source → processor → a silent GainNode (gain=0)
        // instead of directly to destination, to avoid mic feedback/echo.
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        const silentGain = audioContext.createGain();
        silentGain.gain.value = 0; // mute — we don't want to hear ourselves

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;
          const input = e.inputBuffer.getChannelData(0);
          const downsampled = downsample(input, audioContext.sampleRate);
          const pcm = floatTo16BitPCM(downsampled);
          ws.send(pcm);
        };

        source.connect(processor);
        processor.connect(silentGain);
        silentGain.connect(audioContext.destination);
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to access microphone.";
      setError(msg);
      setStatus("error");
    }
  };

  const handleToggle = () => {
    if (status === "idle" || status === "error") {
      startRecording();
    } else if (status === "recording") {
      stopRecording();
    }
  };

  const isRecording = status === "recording";
  const isConnecting = status === "connecting";

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-[var(--color-content)]">
          Live Transcription
        </h1>
        <p className="text-[var(--color-subtle)] text-sm">
          Real-time speech-to-text via WebSockets and Faster-Whisper. Speak
          naturally — transcripts appear after each pause.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2.5 py-3.5 px-5 bg-[rgba(248,113,113,0.1)] border border-[rgba(248,113,113,0.25)] rounded-md text-[var(--color-danger)] text-[0.875rem]">
          <AlertTriangle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {/* Mic button + level meter */}
      <div className="p-8 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)] flex flex-col items-center justify-center gap-6">
        <div className="relative">
          {/* Ping ring while recording */}
          <div
            className={`absolute inset-0 rounded-full transition-all duration-300 ${
              isRecording
                ? "bg-[var(--color-danger)] animate-ping opacity-20"
                : ""
            }`}
          />
          <button
            id="btn-mic-toggle"
            onClick={handleToggle}
            disabled={isConnecting}
            aria-label={isRecording ? "Stop recording" : "Start recording"}
            className={`relative flex items-center justify-center w-20 h-20 rounded-full transition-all duration-300 disabled:opacity-60 disabled:cursor-wait ${
              isRecording
                ? "bg-[var(--color-danger)] text-white shadow-[0_0_24px_rgba(248,113,113,0.45)]"
                : "bg-[var(--color-primary)] text-white hover:brightness-110"
            }`}
          >
            {isConnecting ? (
              <Loader2 size={32} className="animate-spin" />
            ) : isRecording ? (
              <MicOff size={32} />
            ) : (
              <Mic size={32} />
            )}
          </button>
        </div>

        {/* Status label */}
        <div className="flex flex-col items-center gap-1">
          <p className="font-semibold text-lg">
            {isConnecting
              ? "Connecting…"
              : isRecording
                ? "Recording"
                : "Ready to record"}
          </p>
          <p className="text-sm text-[var(--color-subtle)]">
            {isConnecting
              ? "Opening WebSocket connection to backend…"
              : isRecording
                ? "Streaming audio — speak naturally, transcripts appear after each pause."
                : "Click the microphone to start."}
          </p>
        </div>

        {/* Mic level bar */}
        {isRecording && (
          <div
            aria-label="Microphone level"
            className="w-48 h-2 rounded-full bg-[rgba(255,255,255,0.08)] overflow-hidden"
          >
            <div
              className="h-full rounded-full bg-[var(--color-primary)] transition-all duration-75"
              style={{ width: `${Math.round(micLevel * 100)}%` }}
            />
          </div>
        )}
      </div>

      {/* Transcript panel */}
      <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)] flex flex-col gap-4 min-h-[300px]">
        <h2 className="text-[1.05rem] font-semibold flex items-center gap-3">
          <Activity
            size={18}
            className={
              isRecording
                ? "text-[var(--color-primary)] animate-pulse"
                : "text-[var(--color-subtle)]"
            }
          />
          Live Transcript
        </h2>

        <div className="flex flex-col gap-3 flex-1 overflow-y-auto max-h-[400px]">
          {transcript.length === 0 ? (
            <p className="text-[var(--color-subtle)] text-sm italic m-auto">
              {isRecording
                ? "Listening… transcript will appear after each pause."
                : "Transcript will appear here…"}
            </p>
          ) : (
            transcript.map((item, idx) => (
              <div key={idx} className="flex gap-4 animate-fadeIn">
                <span className="text-[var(--color-subtle)] text-xs font-mono mt-1 shrink-0 w-12 text-right">
                  {item.t.toFixed(1)}s
                </span>
                <p className="text-[0.95rem] leading-[1.6] text-[var(--color-content)]">
                  {item.text}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
