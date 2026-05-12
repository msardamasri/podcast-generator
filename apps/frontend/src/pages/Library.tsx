import { useState } from "react";
import {
  Loader2,
  Sparkles,
  Calendar,
  Play,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import {
  usePodcasts,
  useGeneratePodcast,
  usePodcast,
} from "@/hooks/usePodcasts";
import { usePreferences } from "@/hooks/usePreferences";
import { audioUrl } from "@/api/podcasts";
import type { Schedule } from "@/api/types";
import { cn } from "@/lib/cn";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function formatSchedule(s: Schedule | undefined): string | null {
  if (!s || s.type === "on_demand") return null;
  const hh = String(s.hour ?? 0).padStart(2, "0");
  const mm = String(s.minute ?? 0).padStart(2, "0");
  if (s.type === "daily") return `Every day at ${hh}:${mm}`;
  if (s.type === "weekly") {
    const day = WEEKDAYS[s.weekday ?? 0];
    return `Every ${day} at ${hh}:${mm}`;
  }
  return null;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) {
    return `Today, ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return `Yesterday`;
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

function formatDuration(sec: number | null): string {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function StatusDot({ status }: { status: string }) {
  if (status === "ready") return null;
  if (status === "failed")
    return <AlertCircle size={14} className="text-red-400 shrink-0" />;
  return <Loader2 size={14} className="text-accent animate-spin shrink-0" />;
}

export function Library() {
  const { data: prefs } = usePreferences();
  const { data: podcasts, isLoading } = usePodcasts();
  const generate = useGeneratePodcast();
  const [activeId, setActiveId] = useState<string | null>(null);
  const { data: active } = usePodcast(activeId, { poll: true });

  const scheduleText = formatSchedule(prefs?.schedule);
  const hasSchedule = !!scheduleText;

  const onGenerate = async () => {
    if (!prefs) return;
    const res = await generate.mutateAsync(prefs);
    setActiveId(res.podcast_id);
  };

  return (
    <div>
      <header className="mb-12">
        <h1 className="text-4xl font-semibold tracking-tight mb-3">
          Your library
        </h1>
        <p className="text-muted">
          Personalized news podcasts based on what you care about.
        </p>
      </header>

      {/* Action card — schedule status + generate button */}
      <div className="card mb-10 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
              hasSchedule ? "bg-accent/10" : "bg-surface-elevated"
            )}
          >
            {hasSchedule ? (
              <Calendar size={18} className="text-accent" />
            ) : (
              <Sparkles size={18} className="text-muted" />
            )}
          </div>
          <div>
            <div className="text-sm font-medium">
              {hasSchedule ? scheduleText : "On-demand only"}
            </div>
            <div className="text-xs text-muted mt-0.5">
              {hasSchedule
                ? "Next episode generates automatically"
                : "Configure a schedule in Preferences"}
            </div>
          </div>
        </div>

        <button
          onClick={onGenerate}
          disabled={generate.isPending || !prefs}
          className="btn-primary"
        >
          {generate.isPending ? (
            <Loader2 className="animate-spin" size={14} />
          ) : (
            <Sparkles size={14} />
          )}
          {hasSchedule ? "Generate now" : "Generate first episode"}
        </button>
      </div>

      {/* Active podcast — generating or playing */}
      {active && active.status !== "ready" && active.status !== "failed" && (
        <div className="card mb-4 border-accent/30 bg-accent/5">
          <div className="flex items-center gap-3">
            <Loader2 className="animate-spin text-accent" size={18} />
            <div>
              <div className="text-sm font-medium">Generating your podcast</div>
              <div className="text-xs text-muted mt-0.5 capitalize">
                {active.status === "pending" ? "Queued" : active.status}…
              </div>
            </div>
          </div>
        </div>
      )}

      {active && active.status === "ready" && active.audio_path && (
        <div className="card mb-10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                <Play size={16} className="text-accent" fill="currentColor" />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">
                  {active.title ?? "Latest episode"}
                </div>
                <div className="text-xs text-muted mt-0.5">
                  {formatDuration(active.duration_sec)} ·{" "}
                  {formatDate(active.created_at)}
                </div>
              </div>
            </div>
          </div>
          <audio
            controls
            className="w-full"
            src={audioUrl(active.audio_path)}
          />
        </div>
      )}

      {/* Episode list */}
      <div>
        <h2 className="section-title mb-1">All episodes</h2>
        <p className="section-desc mb-5">
          {podcasts?.total ?? 0}{" "}
          {podcasts?.total === 1 ? "episode" : "episodes"}
        </p>

        {isLoading && <div className="text-muted text-sm">Loading…</div>}

        {!isLoading && podcasts?.items.length === 0 && (
          <div className="card text-center py-16">
            <Sparkles size={20} className="text-muted mx-auto mb-3" />
            <div className="text-sm font-medium mb-1">No episodes yet</div>
            <div className="text-xs text-muted">
              Click <span className="text-accent">Generate now</span> above to
              create your first.
            </div>
          </div>
        )}

        <div className="card p-0 overflow-hidden">
          {podcasts?.items
            .filter((p) => p.id !== activeId)
            .map((p, idx) => (
              <button
                key={p.id}
                onClick={() => setActiveId(p.id)}
                className={cn(
                  "w-full text-left flex items-center justify-between px-6 py-4 hover:bg-surface-elevated/50 transition duration-150",
                  idx > 0 && "border-t border-border"
                )}
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-surface-elevated flex items-center justify-center shrink-0 group-hover:bg-accent/10 transition">
                    {p.status === "ready" ? (
                      <Play size={13} className="text-muted" fill="currentColor" />
                    ) : p.status === "failed" ? (
                      <AlertCircle size={14} className="text-red-400" />
                    ) : (
                      <Loader2 size={14} className="text-accent animate-spin" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">
                      {p.title ?? "Untitled"}
                    </div>
                    <div className="text-xs text-muted mt-0.5 flex items-center gap-2">
                      {p.status === "ready" ? (
                        <>
                          <Clock size={11} />
                          <span>{formatDuration(p.duration_sec)}</span>
                          <span className="opacity-50">·</span>
                          <span>{formatDate(p.created_at)}</span>
                        </>
                      ) : (
                        <span className="capitalize">{p.status}</span>
                      )}
                    </div>
                  </div>
                </div>
                {p.status === "ready" && (
                  <CheckCircle2 size={14} className="text-muted/30 shrink-0" />
                )}
              </button>
            ))}
        </div>
      </div>
    </div>
  );
}