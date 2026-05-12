export interface Interest {
  label: string;
  weight: number;
}

export interface Schedule {
  type: "on_demand" | "daily" | "weekly";
  hour?: number | null;
  minute?: number | null;
  weekday?: number | null;
  tz: string;
}

export interface Preferences {
  interests: Interest[];
  exclusions: string[];
  length_min: 2 | 4 | 7;
  tone: "conversational" | "formal" | "energetic";
  voice_id: string;
  schedule: Schedule;
}

export interface PodcastSummary {
  id: string;
  title: string | null;
  status: string;
  duration_sec: number | null;
  created_at: string;
  ready_at: string | null;
}

export interface Segment {
  idx: number;
  title: string;
  source_url: string;
  source_outlet: string;
  start_sec: number | null;
  end_sec: number | null;
}

export interface PodcastDetail extends PodcastSummary {
  audio_path: string | null;
  transcript: string | null;
  error: string | null;
  cost_cents: number;
  segments: Segment[];
}

export interface EnqueueResponse {
  podcast_id: string;
  task_id: string;
  status: string;
}

// ---------- Admin metrics ----------

export interface KPIMetrics {
  total_podcasts: number;
  success_rate: number;
  avg_duration_sec: number;
  avg_cost_cents: number;
  total_failures: number;
}

export interface TimeSeriesPoint {
  date: string;
  completed: number;
  failed: number;
}

export interface OutletShare {
  outlet: string;
  count: number;
}

export interface EventLog {
  id: number;
  type: string;
  properties: Record<string, unknown>;
  created_at: string;
}

export interface AdminMetrics {
  kpis: KPIMetrics;
  timeseries: TimeSeriesPoint[];
  outlets: OutletShare[];
  recent_events: EventLog[];
}