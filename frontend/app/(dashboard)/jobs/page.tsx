"use client";
import useSWR from "swr";
import Link from "next/link";
import { Clock, CheckCircle2, XCircle, Loader2, FileAudio } from "lucide-react";
import { api, Job } from "@/lib/api";

function StatusBadge({ status }: { status: Job["status"] }) {
  const map: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
    pending:    { cls: "badge badge-muted",    icon: <Clock size={11} />,        label: "Pending" },
    processing: { cls: "badge badge-warning",  icon: <Loader2 size={11} className="spin" />,      label: "Processing" },
    completed:  { cls: "badge badge-success",  icon: <CheckCircle2 size={11} />, label: "Completed" },
    failed:     { cls: "badge badge-danger",   icon: <XCircle size={11} />,      label: "Failed" },
  };
  const { cls, icon, label } = map[status] ?? map.pending;
  return <span className={cls}>{icon} {label}</span>;
}

function fmt(s: string) {
  return new Date(s).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

function fmtDuration(s: number | null) {
  if (!s) return "—";
  const m = Math.floor(s / 60), sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export default function JobsPage() {
  const { data: jobs, isLoading, mutate } = useSWR<Job[]>(
    "jobs",
    () => api.listJobs(),
    { refreshInterval: 5000 }
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Processing Jobs</h1>
        <button className="btn btn-ghost" onClick={() => mutate()}>Refresh</button>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-1.5">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 mb-2 skeleton" />
          ))}
        </div>
      ) : !jobs?.length ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center text-[var(--color-subtle)]">
          <FileAudio size={40} className="opacity-30" />
          <p>No jobs yet. <Link href="/upload" className="text-[var(--color-primary-light)]">Upload a file</Link> to get started.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="grid grid-cols-[2fr_1fr_1fr_1.5fr_40px] items-center px-4 py-3 gap-4 text-xs font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em] pb-2">
            <span>File</span>
            <span>Status</span>
            <span>Duration</span>
            <span>Created</span>
            <span></span>
          </div>
          {jobs.map(job => (
            <Link key={job.id} href={`/jobs/${job.id}`} className="grid grid-cols-[2fr_1fr_1fr_1.5fr_40px] items-center px-4 py-3 gap-4 rounded-md cursor-pointer transition-all duration-150 hover:translate-x-[3px] hover:shadow-[0_2px_16px_rgba(0,0,0,0.2)] bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
              <span className="font-medium text-[0.9rem] truncate">{job.file_name || job.id.slice(0, 12)}</span>
              <span><StatusBadge status={job.status} /></span>
              <span className="text-[0.82rem] text-[var(--color-subtle)]">{fmtDuration(job.duration_s)}</span>
              <span className="text-[0.82rem] text-[var(--color-subtle)]">{fmt(job.created_at)}</span>
              <span className="text-[var(--color-subtle)] text-right">→</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
