import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  CheckCircle2,
  Clock,
  DollarSign,
  Loader2,
  Activity,
  AlertCircle,
} from "lucide-react";
import { useAdminMetrics } from "@/hooks/useAdminMetrics";
import type { EventLog } from "@/api/types";
import { cn } from "@/lib/cn";

const ACCENT = "#FF6B35";
const RED = "#F87171";
const MUTED = "#82828c";

function formatDuration(sec: number): string {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatCents(c: number): string {
  if (c < 100) return `${c.toFixed(1)}¢`;
  return `$${(c / 100).toFixed(2)}`;
}

function formatPercent(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDay(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

const EVENT_COLORS: Record<string, string> = {
  podcast_requested: "text-accent",
  podcast_completed: "text-emerald-400",
  podcast_failed: "text-red-400",
  preferences_updated: "text-blue-400",
};

export function Admin() {
  const { data, isLoading, error } = useAdminMetrics();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted text-sm">
        <Loader2 size={14} className="animate-spin" /> Loading metrics…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card flex items-center gap-3">
        <AlertCircle size={18} className="text-red-400" />
        <div className="text-sm">Failed to load metrics</div>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-12">
        <h1 className="text-4xl font-semibold tracking-tight mb-3">Admin</h1>
        <p className="text-muted">
          Real-time metrics from the events table.
        </p>
      </header>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4 mb-10">
        <KPICard
          label="Total podcasts"
          value={data.kpis.total_podcasts.toString()}
          icon={<Activity size={14} />}
        />
        <KPICard
          label="Success rate"
          value={formatPercent(data.kpis.success_rate)}
          icon={<CheckCircle2 size={14} />}
          accent
        />
        <KPICard
          label="Avg duration"
          value={formatDuration(data.kpis.avg_duration_sec)}
          icon={<Clock size={14} />}
        />
        <KPICard
          label="Avg cost"
          value={formatCents(data.kpis.avg_cost_cents)}
          icon={<DollarSign size={14} />}
        />
      </div>

      {/* Timeseries */}
      <section className="mb-10">
        <h2 className="section-title">Generation activity</h2>
        <p className="section-desc mb-5">
          Podcasts completed and failed over the last 14 days.
        </p>

        <div className="card">
          <div className="h-72 -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={data.timeseries.map((p) => ({
                  ...p,
                  label: formatDay(p.date),
                }))}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgb(38 38 42)"
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  stroke={MUTED}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={MUTED}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgb(22 22 25)",
                    border: "1px solid rgb(38 38 42)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "rgb(245 245 247)" }}
                />
                <Line
                  type="monotone"
                  dataKey="completed"
                  stroke={ACCENT}
                  strokeWidth={2}
                  dot={{ fill: ACCENT, r: 3 }}
                  activeDot={{ r: 5 }}
                  name="Completed"
                />
                <Line
                  type="monotone"
                  dataKey="failed"
                  stroke={RED}
                  strokeWidth={2}
                  dot={{ fill: RED, r: 3 }}
                  activeDot={{ r: 5 }}
                  name="Failed"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-6 mt-2 ml-2">
            <LegendDot color={ACCENT} label="Completed" />
            <LegendDot color={RED} label="Failed" />
          </div>
        </div>
      </section>

      {/* Two-column: outlets + events */}
      <div className="grid grid-cols-5 gap-4">
        <section className="col-span-3">
          <h2 className="section-title">Source outlets</h2>
          <p className="section-desc mb-5">
            Where the news comes from, by segment count.
          </p>

          <div className="card">
            {data.outlets.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">
                No segments yet.
              </div>
            ) : (
              <div className="h-72 -mx-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.outlets}
                    layout="vertical"
                    margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgb(38 38 42)"
                      horizontal={false}
                    />
                    <XAxis
                      type="number"
                      stroke={MUTED}
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      allowDecimals={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="outlet"
                      stroke={MUTED}
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      width={130}
                    />
                    <Tooltip
                      cursor={{ fill: "rgb(38 38 42 / 0.5)" }}
                      contentStyle={{
                        background: "rgb(22 22 25)",
                        border: "1px solid rgb(38 38 42)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Bar
                      dataKey="count"
                      fill={ACCENT}
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </section>

        <section className="col-span-2">
          <h2 className="section-title">Recent events</h2>
          <p className="section-desc mb-5">Last 15 from the audit log.</p>

          <div className="card p-0 overflow-hidden">
            {data.recent_events.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">
                No events.
              </div>
            ) : (
              data.recent_events.map((e, i) => (
                <EventRow key={e.id} event={e} first={i === 0} />
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function KPICard({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 text-muted mb-3">
        <span className={accent ? "text-accent" : "text-muted"}>{icon}</span>
        <span className="text-xs">{label}</span>
      </div>
      <div
        className={cn(
          "text-2xl font-semibold tracking-tight",
          accent && "text-accent"
        )}
      >
        {value}
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      <span
        className="w-2.5 h-2.5 rounded-full"
        style={{ background: color }}
      />
      {label}
    </div>
  );
}

function EventRow({ event, first }: { event: EventLog; first: boolean }) {
  const colorClass = EVENT_COLORS[event.type] ?? "text-muted";
  const label = event.type.replace(/_/g, " ");

  return (
    <div
      className={cn(
        "px-4 py-3 flex items-center justify-between gap-3",
        !first && "border-t border-border"
      )}
    >
      <div className="min-w-0 flex-1">
        <div className={cn("text-xs font-medium capitalize", colorClass)}>
          {label}
        </div>
        <div className="text-[11px] text-muted mt-0.5 truncate">
          {formatProperties(event.properties)}
        </div>
      </div>
      <div className="text-[11px] text-muted shrink-0">
        {formatDate(event.created_at)}
      </div>
    </div>
  );
}

function formatProperties(props: Record<string, unknown>): string {
  const entries = Object.entries(props);
  if (entries.length === 0) return "—";
  return entries
    .slice(0, 3)
    .map(([k, v]) => `${k}: ${String(v).slice(0, 40)}`)
    .join(" · ");
}