"use client";
import { useState } from "react";
import useSWR from "swr";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import {
  api,
  Job,
  TranscriptChunk,
  AnalyticsMetrics,
  ContradictionPair,
  Report,
} from "@/lib/api";
import {
  Clock,
  Users,
  MessageSquare,
  AlertTriangle,
  Loader2,
  FileText,
  Download,
} from "lucide-react";
import TopicClusterMap from "@/components/TopicClusterMap";

const COLORS = [
  "#6366f1",
  "#22d3ee",
  "#34d399",
  "#fbbf24",
  "#f87171",
  "#a78bfa",
];

function fmtDur(s: number) {
  const m = Math.floor(s / 60),
    sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function JobHeader({ job }: { job: Job }) {
  const statusColor: Record<string, string> = {
    pending: "badge-muted",
    processing: "badge-warning",
    completed: "badge-success",
    failed: "badge-danger",
  };
  return (
    <div className="flex items-start justify-between flex-wrap gap-4">
      <div>
        <p className="text-[1.4rem] font-bold">{job.file_name || job.id}</p>
        <p className="text-[0.82rem] text-[var(--color-subtle)] mt-1">
          {job.duration_s ? fmtDur(job.duration_s) : "Unknown duration"} ·
          {job.file_size_bytes
            ? ` ${(job.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
            : ""}
        </p>
      </div>
      <span className={`badge ${statusColor[job.status]}`}>{job.status}</span>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }: any) {
  return (
    <div className="flex items-center gap-3.5 p-4 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <div
        className="flex items-center justify-center w-10 h-10 bg-[rgba(255,255,255,0.05)] rounded-lg shrink-0"
        style={{ color }}
      >
        <Icon size={20} />
      </div>
      <div>
        <p className="text-xl font-bold">{value}</p>
        <p className="text-xs text-[var(--color-subtle)] mt-0.5">{label}</p>
      </div>
    </div>
  );
}

function TranscriptPanel({ chunks }: { chunks: TranscriptChunk[] }) {
  return (
    <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <h2 className="text-[1.05rem] font-semibold mb-5 flex items-center gap-3">
        Transcript
      </h2>
      <div className="flex flex-col gap-4 max-h-[480px] overflow-y-auto pr-2">
        {chunks.map((c) => (
          <div key={c.id} className="flex flex-col gap-1.5">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-[var(--color-primary-light)] uppercase tracking-[0.06em]">
                {c.speaker_id || "Unknown"}
              </span>
              <span className="text-xs text-[var(--color-subtle)]">
                {fmtDur(c.start_s)}
              </span>
            </div>
            <p className="text-[0.9rem] leading-[1.6] text-[var(--color-content)]">
              {c.text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function AnalyticsPanel({ metrics }: { metrics: AnalyticsMetrics }) {
  const pieData = metrics.speakers.map((s) => ({
    name: s.speaker_id,
    value: Math.round(s.speaking_time_s),
  }));

  // Flatten wpm_timeline from all speakers for chart
  const wpmData = metrics.speakers
    .flatMap((s) =>
      s.wpm_timeline.map((pt) => ({ t: pt.t, [s.speaker_id]: pt.wpm })),
    )
    .sort((a, b) => a.t - b.t);

  return (
    <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <h2 className="text-[1.05rem] font-semibold mb-5 flex items-center gap-3">
        Behavioral Analytics
      </h2>
      <div className="flex gap-6 flex-wrap mb-6">
        {/* Speaking time pie */}
        <div className="flex-1 min-w-[240px]">
          <p className="text-xs font-semibold text-[var(--color-subtle)] mb-3 uppercase tracking-[0.06em]">
            Speaking Balance
          </p>
          <PieChart width={260} height={200}>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label
            >
              {pieData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Legend />
          </PieChart>
        </div>

        {/* WPM area chart */}
        <div className="flex-[2] min-w-[240px]">
          <p className="text-xs font-semibold text-[var(--color-subtle)] mb-3 uppercase tracking-[0.06em]">
            WPM Timeline
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={wpmData}>
              <defs>
                {metrics.speakers.map((s, i) => (
                  <linearGradient
                    key={s.speaker_id}
                    id={`g${i}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor={COLORS[i]} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS[i]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
              />
              <XAxis
                dataKey="t"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                tickFormatter={(v) => fmtDur(v)}
              />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#111827",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                }}
              />
              {metrics.speakers.map((s, i) => (
                <Area
                  key={s.speaker_id}
                  type="monotone"
                  dataKey={s.speaker_id}
                  stroke={COLORS[i]}
                  fill={`url(#g${i})`}
                  strokeWidth={2}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Speaker stats table */}
      <div className="flex flex-col gap-1.5">
        <div className="grid grid-cols-[1.5fr_1fr_1.5fr_1fr_1fr] px-4 py-2 text-[0.72rem] font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em]">
          <span>Speaker</span>
          <span>WPM</span>
          <span>Fillers</span>
          <span>Pauses</span>
          <span>Confidence</span>
        </div>
        {metrics.speakers.map((s, i) => (
          <div
            key={s.speaker_id}
            className="grid grid-cols-[1.5fr_1fr_1.5fr_1fr_1fr] px-4 py-2.5 rounded-md text-[0.85rem] gap-2 items-center bg-[var(--color-elevated)] border border-[rgba(255,255,255,0.08)]"
          >
            <span style={{ color: COLORS[i], fontWeight: 600 }}>
              {s.speaker_id}
            </span>
            <span>{s.avg_wpm}</span>
            <span>
              {s.filler_count}{" "}
              <small>({(s.filler_rate * 100).toFixed(1)}%)</small>
            </span>
            <span>{s.pause_count}</span>
            <span>{(s.avg_confidence * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ContradictionsPanel({ pairs }: { pairs: ContradictionPair[] }) {
  if (!pairs.length)
    return (
      <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
        <h2 className="text-[1.05rem] font-semibold mb-5 flex items-center gap-3">
          Contradictions
        </h2>
        <p className="text-[0.9rem] text-[var(--color-subtle)]">
          No contradictions detected.
        </p>
      </div>
    );
  return (
    <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <h2 className="text-[1.05rem] font-semibold mb-5 flex items-center gap-3">
        Contradictions{" "}
        <span className="badge badge-danger">{pairs.length}</span>
      </h2>
      <div className="flex flex-col gap-4">
        {pairs.map((p) => (
          <div
            key={p.id}
            className="flex gap-4 p-4 rounded-md bg-[var(--color-elevated)] border border-[rgba(255,255,255,0.08)]"
          >
            <div className="flex flex-col items-center gap-1 text-[var(--color-danger)] text-sm font-bold min-w-[44px]">
              <AlertTriangle size={14} />
              {(p.score * 100).toFixed(0)}%
            </div>
            <div className="flex-1 flex flex-col gap-2">
              <blockquote className="text-[0.875rem] leading-[1.5] py-2 px-3 border-l-3 border-[rgba(255,255,255,0.08)] text-[var(--color-subtle)]">
                <span className="text-[var(--color-content)] font-semibold">
                  {p.speaker_a || "Speaker A"}:{" "}
                </span>
                {p.text_a || `Chunk ${p.chunk_a_id.slice(0, 8)}`}
              </blockquote>
              <blockquote className="text-[0.875rem] leading-[1.5] py-2 px-3 border-l-3 border-[rgba(255,255,255,0.08)] text-[var(--color-subtle)]">
                <span className="text-[var(--color-content)] font-semibold">
                  {p.speaker_b || "Speaker B"}:{" "}
                </span>
                {p.text_b || `Chunk ${p.chunk_b_id.slice(0, 8)}`}
              </blockquote>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReportPanel({ jobId }: { jobId: string }) {
  const {
    data: report,
    error,
    mutate,
  } = useSWR<Report>(`report/${jobId}`, () => api.getReport(jobId), {
    shouldRetryOnError: false,
  });
  const [generating, setGenerating] = useState(false);

  const generate = async () => {
    setGenerating(true);
    try {
      await api.generateReport(jobId);
      mutate();
    } catch (e: any) {
      alert(
        "Failed to generate report: " + (e.response?.data?.detail || e.message),
      );
    }
    setGenerating(false);
  };

  if (error && error.response?.status === 404) {
    return (
      <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)] flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-[1.05rem] font-semibold mb-1 flex items-center gap-2">
            <FileText size={18} /> Executive Report
          </h2>
          <p className="text-sm text-[var(--color-subtle)]">
            AI-generated summary, key decisions, and action items.
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={generate}
          disabled={generating}
        >
          {generating ? (
            <>
              <Loader2 size={15} className="spin" /> Generating…
            </>
          ) : (
            "Generate Report"
          )}
        </button>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-4">
        <h2 className="text-[1.05rem] font-semibold flex items-center gap-2">
          <FileText size={18} /> Executive Report
        </h2>
        <button
          className="btn btn-ghost text-sm"
          onClick={() => api.downloadPdf(jobId)}
        >
          <Download size={15} /> Download PDF
        </button>
      </div>
      <div className="flex flex-col gap-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em] mb-2">
            Summary
          </h3>
          <p className="text-[0.9rem] leading-[1.6] text-[var(--color-content)]">
            {report.summary}
          </p>
        </div>
        <div className="flex gap-6 flex-wrap">
          <div className="flex-1 min-w-[240px]">
            <h3 className="text-sm font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em] mb-2">
              Decisions
            </h3>
            <ul className="list-disc pl-4 text-[0.9rem] leading-[1.6] text-[var(--color-content)] flex flex-col gap-1">
              {report.decisions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          </div>
          <div className="flex-1 min-w-[240px]">
            <h3 className="text-sm font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em] mb-2">
              Action Items
            </h3>
            <ul className="list-disc pl-4 text-[0.9rem] leading-[1.6] text-[var(--color-content)] flex flex-col gap-1">
              {report.action_items.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;

  const { data: job } = useSWR<Job>(`job/${id}`, () => api.getJob(id), {
    refreshInterval: 4000,
  });
  const { data: chunks } = useSWR<TranscriptChunk[]>(
    job?.status === "completed" ? `transcript/${id}` : null,
    () => api.getTranscript(id),
  );
  const { data: metrics } = useSWR<AnalyticsMetrics>(
    job?.status === "completed" ? `analytics/${id}` : null,
    () => api.getAnalytics(id),
  );
  const { data: contras } = useSWR<ContradictionPair[]>(
    job?.status === "completed" ? `contradictions/${id}` : null,
    () => api.getContradictions(id),
  );

  if (!job)
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-[var(--color-subtle)]">
        <Loader2 size={32} className="spin" />
        <p>Loading job…</p>
      </div>
    );

  return (
    <div className="flex flex-col gap-6">
      <JobHeader job={job} />

      {job.status === "completed" && metrics && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4">
          <StatCard
            label="Total Words"
            value={metrics.total_words.toLocaleString()}
            icon={MessageSquare}
            color="#6366f1"
          />
          <StatCard
            label="Speakers"
            value={metrics.speakers.length}
            icon={Users}
            color="#22d3ee"
          />
          <StatCard
            label="Duration"
            value={fmtDur(metrics.total_duration_s)}
            icon={Clock}
            color="#34d399"
          />
          <StatCard
            label="Interruptions"
            value={metrics.interruptions.length}
            icon={AlertTriangle}
            color="#fbbf24"
          />
        </div>
      )}

      {job.status === "processing" && (
        <div className="flex items-center gap-4 py-4 px-6 text-[var(--color-warning)] text-[0.9rem] bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)] rounded-xl">
          <Loader2 size={22} className="spin" />
          <p>AI pipeline running… this page refreshes automatically.</p>
        </div>
      )}

      {job.status === "failed" && (
        <div className="flex items-center gap-2.5 py-3.5 px-5 bg-[rgba(248,113,113,0.1)] border border-[rgba(248,113,113,0.25)] rounded-md text-[var(--color-danger)] text-[0.875rem]">
          <AlertTriangle size={16} />{" "}
          {job.error_message || "Processing failed."}
        </div>
      )}

      {chunks && chunks.length > 0 && <TranscriptPanel chunks={chunks} />}
      {metrics && <AnalyticsPanel metrics={metrics} />}
      {metrics && (metrics as any).topic_segments && (
        <TopicClusterMap topics={(metrics as any).topic_segments} />
      )}
      {contras && <ContradictionsPanel pairs={contras} />}
      {job.status === "completed" && <ReportPanel jobId={job.id} />}
    </div>
  );
}
