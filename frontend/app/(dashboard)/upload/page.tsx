"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileAudio, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";

type State = "idle" | "uploading" | "success" | "error";

const ACCEPTED = ["audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg", "audio/flac", "video/mp4", "video/webm"];
const MAX_MB = 500;

export default function UploadPage() {
  const router = useRouter();
  const [state, setState] = useState<State>("idle");
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState("");

  const validate = (f: File): string | null => {
    if (!ACCEPTED.includes(f.type) && !f.name.match(/\.(mp3|wav|mp4|ogg|flac|webm|m4a)$/i))
      return "Unsupported file type. Use MP3, WAV, MP4, OGG, or FLAC.";
    if (f.size > MAX_MB * 1024 * 1024)
      return `File too large (max ${MAX_MB} MB).`;
    return null;
  };

  const handleFile = useCallback((f: File) => {
    const err = validate(f);
    if (err) { setError(err); return; }
    setFile(f);
    setError("");
  }, []);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const submit = async () => {
    if (!file) return;
    setState("uploading");
    setProgress(0);

    // Fake progress bar while uploading
    const iv = setInterval(() => setProgress(p => Math.min(p + 8, 85)), 200);
    try {
      const res = await api.uploadFile(file);
      clearInterval(iv);
      setProgress(100);
      setJobId(res.job_id);
      setState("success");
      setTimeout(() => router.push(`/jobs/${res.job_id}`), 1800);
    } catch (e: any) {
      clearInterval(iv);
      setError(e?.response?.data?.detail || "Upload failed. Is the API running?");
      setState("error");
    }
  };

  const fmtSize = (b: number) =>
    b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${(b / 1024).toFixed(0)} KB`;

  return (
    <div className="flex flex-col gap-6 max-w-[640px]">
      <h1 className="text-3xl font-bold">Upload Audio / Video</h1>
      <p className="text-[var(--color-subtle)] text-[0.9rem] leading-[1.6]">
        Drop an audio or video file to start the full AI processing pipeline —
        transcription → diarization → embeddings → analytics.
      </p>

      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-12 flex items-center justify-center cursor-pointer transition-all ${drag || file ? "border-[var(--color-primary)] bg-[rgba(99,102,241,0.05)]" : "border-[rgba(255,255,255,0.08)] bg-[var(--color-surface)] hover:border-[var(--color-primary)] hover:bg-[rgba(99,102,241,0.05)]"} ${file ? "border-solid" : ""}`}
        onDragOver={e => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <input id="file-input" type="file" accept={ACCEPTED.join(",")} hidden onChange={onInput} />
        {file ? (
          <div className="flex items-center gap-4">
            <FileAudio size={36} className="text-[var(--color-primary-light)] shrink-0" />
            <div>
              <p className="font-semibold text-[0.95rem]">{file.name}</p>
              <p className="text-xs text-[var(--color-subtle)] mt-1">{fmtSize(file.size)} · {file.type || "audio"}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2.5 text-center">
            <Upload size={40} className="text-[var(--color-subtle)]" />
            <p className="text-base font-medium">Drag & drop or <span className="text-[var(--color-primary-light)]">browse</span></p>
            <p className="text-xs text-[var(--color-subtle)]">MP3 · WAV · MP4 · OGG · FLAC · WebM · up to {MAX_MB} MB</p>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {state === "uploading" && (
        <div className="h-1 bg-[var(--color-elevated)] rounded-sm overflow-hidden">
          <div className="h-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-accent)] rounded-sm transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
        </div>
      )}

      {/* Error */}
      {(error || state === "error") && (
        <div className="flex items-center gap-2 py-3 px-4 bg-[rgba(248,113,113,0.1)] border border-[rgba(248,113,113,0.25)] rounded-md text-[var(--color-danger)] text-[0.85rem]">
          <AlertCircle size={16} />
          {error || "Something went wrong"}
        </div>
      )}

      {/* Success */}
      {state === "success" && (
        <div className="flex items-center gap-2 py-3 px-4 bg-[rgba(52,211,153,0.1)] border border-[rgba(52,211,153,0.25)] rounded-md text-[var(--color-success)] text-[0.85rem]">
          <CheckCircle size={16} />
          Job created! Redirecting to job {jobId.slice(0, 8)}…
        </div>
      )}

      {/* Submit */}
      <button
        className="btn btn-primary self-start"
        disabled={!file || state === "uploading" || state === "success"}
        onClick={submit}
      >
        {state === "uploading" ? (
          <><Loader2 size={16} className="spin" /> Uploading…</>
        ) : (
          <><Upload size={16} /> Start Processing</>
        )}
      </button>
    </div>
  );
}
