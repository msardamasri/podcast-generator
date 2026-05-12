import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getPreferences, updatePreferences } from "@/api/preferences";
import type { Preferences } from "@/api/types";

export function usePreferences() {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: getPreferences,
  });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prefs: Preferences) => updatePreferences(prefs),
    onSuccess: (data) => {
      qc.setQueryData(["preferences"], data);
    },
  });
}