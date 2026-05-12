import { api } from "./client";
import type { AdminMetrics } from "./types";

export async function getAdminMetrics(): Promise<AdminMetrics> {
  const { data } = await api.get<AdminMetrics>("/admin/metrics");
  return data;
}