"use client";

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ZAxis } from "recharts";

const COLORS = ["#6366f1", "#22d3ee", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#ec4899", "#14b8a6"];

interface TopicSegment {
  topic_id: number;
  name: string;
  count: number;
  x: number;
  y: number;
}

export default function TopicClusterMap({ topics }: { topics: TopicSegment[] }) {
  if (!topics || topics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-[var(--color-subtle)] text-sm h-[300px] border border-[rgba(255,255,255,0.08)] rounded-xl bg-[var(--color-surface)]">
        <p>No topic clusters available for this conversation.</p>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-xl bg-[var(--color-surface)] border border-[rgba(255,255,255,0.08)]">
      <h2 className="text-[1.05rem] font-semibold mb-5 flex items-center gap-3">Semantic Topic Clusters</h2>
      
      <div className="flex gap-6 flex-wrap">
        <div className="flex-[2] min-w-[300px]">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" dataKey="x" name="UMAP X" tick={false} axisLine={false} />
              <YAxis type="number" dataKey="y" name="UMAP Y" tick={false} axisLine={false} />
              <ZAxis type="number" dataKey="count" range={[100, 600]} name="Segments" />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                formatter={(value, name) => [value, name]}
              />
              <Scatter name="Topics" data={topics}>
                {topics.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        
        <div className="flex-1 min-w-[200px] flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-2">
          {topics.sort((a, b) => b.count - a.count).map((t, i) => (
            <div key={t.topic_id} className="flex items-center gap-3 p-3 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)]">
              <div className="w-3 h-3 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
              <div>
                <p className="text-sm font-semibold text-[var(--color-content)] line-clamp-1" title={t.name}>{t.name}</p>
                <p className="text-xs text-[var(--color-subtle)] mt-0.5">{t.count} segments</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
