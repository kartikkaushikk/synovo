"use client";
import { useState } from "react";
import useSWR from "swr";
import { AlertTriangle, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { api, ContradictionPair } from "@/lib/api";

function ScoreMeter({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "#f87171" : pct >= 60 ? "#fbbf24" : "#94a3b8";
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex-1 h-[5px] bg-[rgba(255,255,255,0.08)] rounded-[3px] overflow-hidden max-w-[180px]">
        <div className="h-full rounded-[3px] transition-all duration-500 ease-out" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span style={{ color, fontWeight: 700 }}>{pct}%</span>
    </div>
  );
}

function ContraCard({ pair }: { pair: ContradictionPair }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl overflow-hidden bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <button className="flex items-center justify-between w-full py-4 px-5 bg-transparent border-none cursor-pointer text-[var(--color-content)] text-left gap-4 transition-colors hover:bg-[rgba(255,255,255,0.03)]" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center gap-3">
          <AlertTriangle size={16} className="text-[var(--color-danger)] shrink-0" />
          <div>
            <p className="text-[0.9rem] font-semibold mb-1">
              <span className="text-[#6366f1]">{pair.speaker_a || "Speaker A"}</span>
              &nbsp;↔&nbsp;
              <span className="text-[#22d3ee]">{pair.speaker_b || "Speaker B"}</span>
            </p>
            <ScoreMeter score={pair.score} />
          </div>
        </div>
        {open ? <ChevronUp size={16} className="text-[var(--color-subtle)] shrink-0"/> : <ChevronDown size={16} className="text-[var(--color-subtle)] shrink-0"/>}
      </button>
      {open && (
        <div className="px-5 pb-5 flex flex-col gap-2.5">
          <blockquote className="py-2.5 px-3.5 border-l-3 border-[var(--color-border)] text-[0.875rem] leading-[1.55] text-[var(--color-subtle)] rounded-r-md bg-[rgba(255,255,255,0.02)]">
            <span className="text-[#6366f1]">{pair.speaker_a || "A"}: </span>
            {pair.text_a || `Chunk ${pair.chunk_a_id?.slice(0,8)}`}
          </blockquote>
          <blockquote className="py-2.5 px-3.5 border-l-3 border-[var(--color-border)] text-[0.875rem] leading-[1.55] text-[var(--color-subtle)] rounded-r-md bg-[rgba(255,255,255,0.02)]">
            <span className="text-[#22d3ee]">{pair.speaker_b || "B"}: </span>
            {pair.text_b || `Chunk ${pair.chunk_b_id?.slice(0,8)}`}
          </blockquote>
          {pair.explanation && (
            <p className="text-[0.8rem] text-[var(--color-subtle)] italic">{pair.explanation}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const [jobId, setJobId] = useState("");
  const [submitted, setSubmitted] = useState("");

  const { data, isLoading, error } = useSWR<ContradictionPair[]>(
    submitted ? `contradictions/${submitted}` : null,
    () => api.getContradictions(submitted)
  );

  return (
    <div className="flex flex-col gap-6 max-w-[760px]">
      <h1 className="text-3xl font-bold">Contradiction Report</h1>
      <p className="text-[var(--color-subtle)] text-[0.9rem] leading-[1.6]">
        NLI-powered detection of conflicting claims across speakers in a conversation.
      </p>

      <form
        className="flex gap-3"
        onSubmit={e => { e.preventDefault(); setSubmitted(jobId.trim()); }}
      >
        <input
          value={jobId}
          onChange={e => setJobId(e.target.value)}
          placeholder="Enter Job ID…"
          required
          className="max-w-[460px]"
        />
        <button className="btn btn-primary" type="submit">
          <AlertTriangle size={15} /> Analyze
        </button>
      </form>

      {isLoading && (
        <div className="flex justify-center p-12 text-[var(--color-subtle)]"><Loader2 size={24} className="spin" /></div>
      )}

      {error && (
        <div className="py-3 px-4 bg-[rgba(248,113,113,0.1)] border border-[rgba(248,113,113,0.25)] rounded-md text-[var(--color-danger)] text-[0.85rem]">Failed to load contradictions. Is the job completed?</div>
      )}

      {data && (
        <>
          <div className="flex items-center gap-3">
            <span className={data.length ? "badge badge-danger" : "badge badge-success"}>
              {data.length} contradiction{data.length !== 1 ? "s" : ""} found
            </span>
          </div>
          {data.length === 0 && (
            <p className="text-[var(--color-success)] text-[0.9rem]">✓ No contradictions detected in this conversation.</p>
          )}
          <div className="flex flex-col gap-3">
            {data.map(pair => <ContraCard key={pair.id} pair={pair} />)}
          </div>
        </>
      )}
    </div>
  );
}
