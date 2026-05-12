import { api } from "./client";
import type {
  EnqueueResponse,
  PodcastDetail,
  PodcastSummary,
} from "./types";

interface ListResponse {
  items: PodcastSummary[];
  total: number;
}

export async function listPodcasts(): Promise<ListResponse> {
  const { data } = await api.get<ListResponse>("/podcasts");
  return data;
}

export async function getPodcast(id: string): Promise<PodcastDetail> {
  const { data } = await api.get<PodcastDetail>(`/podcasts/${id}`);
  return data;
}

export async function generatePodcast(
  prefs: import("./types").Preferences
): Promise<EnqueueResponse> {
  const { data } = await api.post<EnqueueResponse>("/podcasts/generate", {
    interests: prefs.interests,
    exclusions: prefs.exclusions,
    length_min: prefs.length_min,
    tone: prefs.tone,
    voice_id: prefs.voice_id,
    max_articles: 6,
    since_hours: 24,
  });
  return data;
}

export function audioUrl(filename: string): string {
  return `/api/v1/podcasts/audio/${filename}`;
}