import { api } from "./client";
import type { Preferences } from "./types";

export async function getPreferences(): Promise<Preferences> {
  const { data } = await api.get<Preferences>("/preferences");
  return data;
}

export async function updatePreferences(prefs: Preferences): Promise<Preferences> {
  const { data } = await api.put<Preferences>("/preferences", prefs);
  return data;
}