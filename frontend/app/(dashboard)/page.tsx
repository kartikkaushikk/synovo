"use client";
import Link from "next/link";
import { Upload, Zap, Database, Search, ArrowRight } from "lucide-react";

const FEATURES = [
  {
    icon: Upload,
    title: "Upload & Process",
    desc: "Drop audio/video files and kick off the full AI pipeline instantly.",
    href: "/upload",
    color: "#6366f1",
  },
  {
    icon: Zap,
    title: "Behavioral Analytics",
    desc: "WPM timelines, filler words, pauses, and interruption maps.",
    href: "/jobs",
    color: "#22d3ee",
  },
  {
    icon: Database,
    title: "Vector Search",
    desc: "Semantic search over any conversation using natural language.",
    href: "/search",
    color: "#34d399",
  },
  {
    icon: Search,
    title: "Contradiction Detection",
    desc: "NLI-powered detection of conflicting claims across speakers.",
    href: "/reports",
    color: "#f87171",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-col items-start gap-4 pt-12 pb-4">
        <div className="inline-block px-3.5 py-1.5 bg-[rgba(99,102,241,0.15)] text-[var(--color-primary-light)] border border-[rgba(99,102,241,0.3)] rounded-full text-xs font-semibold tracking-[0.08em] uppercase">
          AI Infrastructure Platform
        </div>
        <h1 className="text-[clamp(2.2rem,5vw,3.5rem)] font-bold leading-[1.15] tracking-[-0.02em]">
          Synovo
          <span className="bg-clip-text text-transparent bg-gradient-to-br from-[var(--color-primary-light)] to-[var(--color-accent)]">
            {" "}
            : AI - Conversational Intelligence
          </span>
        </h1>
        <p className="max-w-[560px] text-[var(--color-subtle)] text-[1.05rem] leading-[1.7]">
          A production-grade AI platform for speech transcription, speaker
          diarization, behavioral analytics, semantic retrieval, and
          contradiction detection.
        </p>
        <div className="flex gap-4 mt-2">
          <Link href="/upload" className="btn btn-primary">
            <Upload size={16} /> Upload Audio
          </Link>
          <Link href="/jobs" className="btn btn-ghost">
            View Jobs <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
        {FEATURES.map(({ icon: Icon, title, desc, href, color }) => (
          <Link
            key={href}
            href={href}
            className="flex flex-col gap-3 p-6 relative cursor-pointer card-glass group"
          >
            <div
              className="flex items-center justify-center w-11 h-11 rounded-xl mb-1"
              style={{ background: `${color}1a`, color }}
            >
              <Icon size={22} />
            </div>
            <h3 className="text-base font-semibold text-white">{title}</h3>
            <p className="text-sm text-[var(--color-subtle)] leading-[1.55] flex-1">
              {desc}
            </p>
            <span className="text-[var(--color-subtle)] mt-auto flex items-center group-hover:text-[var(--color-content)] transition-colors">
              <ArrowRight size={14} />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
