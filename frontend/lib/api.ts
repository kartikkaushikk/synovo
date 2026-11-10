import axios from "axios";

const API = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30_000,
});

// ── Types ─────────────────────────────────────────────────────────────────

export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface Job {
  id: string;
  status: JobStatus;
  file_name: string | null;
  file_size_bytes: number | null;
  duration_s: number | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface TranscriptChunk {
  id: string;
  speaker_id: string | null;
  text: string;
  start_s: number;
  end_s: number;
  confidence: number | null;
  chunk_index: number;
  topic_id: number | null;
}

export interface Speaker {
  id: string;
  label: string;
  total_s: number | null;
  wpm: number | null;
  filler_rate: number | null;
  avg_pause_s: number | null;
  turn_count: number;
}

export interface SearchResult {
  chunk_id: string;
  job_id: string;
  text: string;
  speaker_id: string | null;
  start_s: number;
  end_s: number;
  score: number;
  chunk_index: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  cached: boolean;
  latency_ms: number;
}

export interface ContradictionPair {
  id: string;
  chunk_a_id: string;
  chunk_b_id: string;
  speaker_a?: string;
  text_a?: string;
  speaker_b?: string;
  text_b?: string;
  score: number;
  explanation: string | null;
}

export interface AnalyticsMetrics {
  job_id: string;
  total_duration_s: number;
  total_words: number;
  speakers: Array<{
    speaker_id: string;
    total_words: number;
    speaking_time_s: number;
    speaking_ratio: number;
    avg_wpm: number;
    filler_count: number;
    filler_rate: number;
    pause_count: number;
    avg_confidence: number;
    wpm_timeline: Array<{ t: number; wpm: number }>;
  }>;
  pause_events: Array<{
    speaker: string;
    start: number;
    end: number;
    duration: number;
  }>;
  interruptions: Array<{
    interrupter: string;
    interrupted: string;
    at: number;
  }>;
}

export interface Report {
  job_id: string;
  summary: string;
  decisions: string[];
  action_items: string[];
}

// ── API calls ─────────────────────────────────────────────────────────────

export const api = {
  // Upload
  uploadFile: async (
    file: File,
  ): Promise<{ job_id: string; status: JobStatus }> => {
    const form = new FormData();
    form.append("file", file);
    const { data } = await API.post("/api/v1/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  // Jobs
  listJobs: async (): Promise<Job[]> => {
    const { data } = await API.get("/api/v1/jobs");
    return data;
  },
  getJob: async (jobId: string): Promise<Job> => {
    const { data } = await API.get(`/api/v1/jobs/${jobId}`);
    return data;
  },
  getTranscript: async (jobId: string): Promise<TranscriptChunk[]> => {
    const { data } = await API.get(`/api/v1/jobs/${jobId}/transcript`);
    // Backend returns { job_id, chunks: [...], total_chunks }
    return Array.isArray(data) ? data : (data.chunks ?? []);
  },
  getSpeakers: async (jobId: string): Promise<Speaker[]> => {
    const { data } = await API.get(`/api/v1/jobs/${jobId}/speakers`);
    return data;
  },
  getAnalytics: async (jobId: string): Promise<AnalyticsMetrics> => {
    const { data } = await API.get(`/api/v1/jobs/${jobId}/analytics`);
    return data;
  },
  getContradictions: async (jobId: string): Promise<ContradictionPair[]> => {
    const { data } = await API.get(`/api/v1/jobs/${jobId}/contradictions`);
    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray(data.contradictions)) {
      return data.contradictions;
    }
    return [];
  },

  // Reports
  generateReport: async (jobId: string): Promise<Report> => {
    const { data } = await API.post(`/api/v1/reports/${jobId}/generate`);
    return data;
  },
  getReport: async (jobId: string): Promise<Report> => {
    const { data } = await API.get(`/api/v1/reports/${jobId}`);
    return data;
  },
  downloadPdf: (jobId: string) => {
    window.open(
      `${API.defaults.baseURL}/api/v1/reports/${jobId}/pdf`,
      "_blank",
    );
  },

  // Search
  search: async (
    jobId: string,
    query: string,
    topK = 5,
    speakerFilter?: string,
  ): Promise<SearchResponse> => {
    const { data } = await API.post("/api/v1/search", {
      job_id: jobId,
      query,
      top_k: topK,
      speaker_filter: speakerFilter || null,
    });
    return data;
  },
};
