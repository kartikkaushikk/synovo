"use client";
import { useState } from "react";
import { Search, Loader2, Clock, User, Zap } from "lucide-react";
import { api, SearchResult } from "@/lib/api";

export default function SearchPage() {
  const [jobId, setJobId]     = useState("");
  const [query, setQuery]     = useState("");
  const [topK, setTopK]       = useState(5);
  const [speaker, setSpeaker] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [meta, setMeta]       = useState<{ latency: number; cached: boolean } | null>(null);
  const [error, setError]     = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobId.trim() || !query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.search(jobId.trim(), query.trim(), topK, speaker.trim() || undefined);
      setResults(res.results);
      setMeta({ latency: res.latency_ms, cached: res.cached });
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Search failed.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  function fmtDur(s: number) {
    const m = Math.floor(s / 60), sec = Math.round(s % 60);
    return `${m}:${String(sec).padStart(2,"0")}`;
  }

  return (
    <div className="flex flex-col gap-5 max-w-[820px]">
      <h1 className="text-3xl font-bold">Semantic Search</h1>
      <p className="text-[var(--color-subtle)] text-[0.9rem]">Query any conversation using natural language.</p>

      <form className="flex flex-col gap-4 p-6 bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)] rounded-xl" onSubmit={submit}>
        <div className="flex gap-4 flex-wrap">
          <div className="flex flex-col gap-1.5 flex-1">
            <label className="text-[0.78rem] font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em]">Job ID</label>
            <input
              value={jobId}
              onChange={e => setJobId(e.target.value)}
              placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5 basis-[100px] grow-0 shrink-0">
            <label className="text-[0.78rem] font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em]">Top K</label>
            <input
              type="number" min={1} max={20} value={topK}
              onChange={e => setTopK(+e.target.value)}
            />
          </div>
        </div>
        <div className="flex gap-4 flex-wrap">
          <div className="flex flex-col gap-1.5 flex-1">
            <label className="text-[0.78rem] font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em]">Query</label>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. What did the candidate say about their experience?"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5 basis-[160px] grow-0 shrink-0">
            <label className="text-[0.78rem] font-semibold text-[var(--color-subtle)] uppercase tracking-[0.06em]">Speaker filter</label>
            <input
              value={speaker}
              onChange={e => setSpeaker(e.target.value)}
              placeholder="SPEAKER_00"
            />
          </div>
        </div>
        <button className="btn btn-primary self-start mt-2" disabled={loading}>
          {loading ? <><Loader2 size={15} className="spin" /> Searching…</> : <><Search size={15} /> Search</>}
        </button>
      </form>

      {error && <div className="py-3 px-4 bg-[rgba(248,113,113,0.1)] border border-[rgba(248,113,113,0.25)] rounded-md text-[var(--color-danger)] text-[0.85rem]">{error}</div>}

      {meta && (
        <div className="flex items-center gap-2 text-[0.8rem] text-[var(--color-subtle)]">
          <Zap size={13} /> {meta.latency.toFixed(1)} ms
          {meta.cached && <span className="badge badge-primary ml-2">cached</span>}
          {results && <span className="ml-auto">{results.length} result{results.length !== 1 ? "s" : ""}</span>}
        </div>
      )}

      {results && results.length === 0 && (
        <p className="text-[var(--color-subtle)] text-[0.9rem]">No results found for this query.</p>
      )}

      {results && results.map((r, i) => (
        <div key={r.chunk_id} className="py-4 px-5 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)] fade-in" style={{ animationDelay: `${i * 60}ms` }}>
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex gap-4">
              <span className="flex items-center gap-1 text-[0.78rem] text-[var(--color-primary-light)] font-semibold"><User size={12} /> {r.speaker_id || "Unknown"}</span>
              <span className="flex items-center gap-1 text-[0.78rem] text-[var(--color-subtle)]"><Clock size={12} /> {fmtDur(r.start_s)} – {fmtDur(r.end_s)}</span>
            </div>
            <div className="text-base font-bold" style={{ color: r.score > 0.8 ? "#34d399" : r.score > 0.5 ? "#fbbf24" : "#94a3b8" }}>
              {(r.score * 100).toFixed(0)}%
            </div>
          </div>
          <p className="text-[0.9rem] leading-[1.65] text-[var(--color-content)]">{r.text}</p>
        </div>
      ))}
    </div>
  );
}
