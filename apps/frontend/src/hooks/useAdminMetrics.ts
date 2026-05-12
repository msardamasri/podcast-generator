import { useQuery } from "@tanstack/react-query";
import { getAdminMetrics } from "@/api/admin";

export function useAdminMetrics() {
  return useQuery({
    queryKey: ["admin-metrics"],
    queryFn: getAdminMetrics,
    refetchInterval: 30_000, // refresh every 30s
  });
}