import { useState } from "react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { usePodcasts, useGeneratePodcast, usePodcast } from "@/hooks/usePodcasts";
import { usePreferences } from "@/hooks/usePreferences";
import { audioUrl } from "@/api/podcasts";
import { Loader2 } from "lucide-react";

export function Library() {
  const { data: prefs } = usePreferences();
  const { data: podcasts, isLoading } = usePodcasts();
  const generate = useGeneratePodcast();
  const [activeId, setActiveId] = useState<string | null>(null);

  const { data: active } = usePodcast(activeId, { poll: true });

  const onGenerate = async () => {
    if (!prefs) return;
    const res = await generate.mutateAsync(prefs);
    setActiveId(res.podcast_id);
  };

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Library</h1>
        <Button onClick={onGenerate} disabled={generate.isPending || !prefs}>
          {generate.isPending && <Loader2 className="animate-spin" size={16} />}
          Generate now
        </Button>
      </div>

      {active && active.status !== "ready" && active.status !== "failed" && (
        <Card className="mb-4">
          <div className="flex items-center gap-3">
            <Loader2 className="animate-spin text-accent" size={20} />
            <div className="text-sm">
              <div className="font-medium">Generating podcast...</div>
              <div className="text-muted capitalize">{active.status}</div>
            </div>
          </div>
        </Card>
      )}

      {active && active.status === "ready" && active.audio_path && (
        <Card className="mb-4">
          <div className="font-medium mb-2">{active.title}</div>
          <audio
            controls
            className="w-full"
            src={audioUrl(active.audio_path)}
          />
        </Card>
      )}

      {isLoading && <div className="text-muted">Loading...</div>}

      <div className="space-y-2">
        {podcasts?.items.map((p) => (
          <Card
            key={p.id}
            className="cursor-pointer hover:border-accent transition"
          >
            <div
              className="flex items-center justify-between"
              onClick={() => setActiveId(p.id)}
            >
              <div>
                <div className="font-medium">{p.title ?? "Untitled"}</div>
                <div className="text-xs text-muted">
                  {p.status} · {p.duration_sec ? `${p.duration_sec}s` : "—"}
                </div>
              </div>
              <div className="text-xs text-muted">
                {new Date(p.created_at).toLocaleString()}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}