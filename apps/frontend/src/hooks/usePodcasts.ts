import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generatePodcast,
  getPodcast,
  listPodcasts,
} from "@/api/podcasts";
import type { Preferences } from "@/api/types";

export function usePodcasts() {
  return useQuery({
    queryKey: ["podcasts"],
    queryFn: listPodcasts,
  });
}

export function usePodcast(id: string | null, opts?: { poll?: boolean }) {
  return useQuery({
    queryKey: ["podcast", id],
    queryFn: () => getPodcast(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      if (!opts?.poll) return false;
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 2000;
    },
  });
}

export function useGeneratePodcast() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prefs: Preferences) => generatePodcast(prefs),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["podcasts"] });
    },
  });
}