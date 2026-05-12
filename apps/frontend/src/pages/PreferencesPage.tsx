import { useEffect, useState } from "react";
import { X, Plus, Check } from "lucide-react";
import { usePreferences, useUpdatePreferences } from "@/hooks/usePreferences";
import type { Preferences } from "@/api/types";
import { cn } from "@/lib/cn";

const PRESET_TOPICS = [
  "artificial intelligence and machine learning",
  "startups and venture capital",
  "macroeconomics and markets",
  "climate and sustainability",
  "space and astronomy",
  "Formula 1 racing",
  "football",
  "world news",
  "science and research",
  "biotech and pharma",
];

const VOICES = [
  { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel", desc: "Warm, neutral" },
  { id: "pNInz6obpgDQGcFmaJgB", name: "Adam", desc: "Calm, narrative" },
  { id: "nPczCjzI2devNBz1zQrb", name: "Brian", desc: "Deep, authoritative" },
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Sarah", desc: "Younger, casual" },
];

const LENGTHS = [
  { value: 2 as const, label: "Quick", desc: "~2 min · headlines" },
  { value: 4 as const, label: "Standard", desc: "~4 min · daily briefing" },
  { value: 7 as const, label: "Deep", desc: "~6 min · context & analysis" },
];

const TONES = [
  { value: "conversational" as const, label: "Conversational" },
  { value: "formal" as const, label: "Formal" },
  { value: "energetic" as const, label: "Energetic" },
];

export function PreferencesPage() {
  const { data, isLoading } = usePreferences();
  const update = useUpdatePreferences();
  const [draft, setDraft] = useState<Preferences | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  if (isLoading || !draft) {
    return <div className="text-muted text-sm">Loading…</div>;
  }

  const toggleTopic = (label: string) => {
    const exists = draft.interests.find((i) => i.label === label);
    setDraft({
      ...draft,
      interests: exists
        ? draft.interests.filter((i) => i.label !== label)
        : [...draft.interests, { label, weight: 1.0 }],
    });
  };

  const addCustom = (label: string) => {
    const trimmed = label.trim();
    if (!trimmed || draft.interests.find((i) => i.label === trimmed)) return;
    setDraft({
      ...draft,
      interests: [...draft.interests, { label: trimmed, weight: 1.0 }],
    });
  };

  const removeInterest = (label: string) =>
    setDraft({
      ...draft,
      interests: draft.interests.filter((i) => i.label !== label),
    });

  const addExclusion = (label: string) => {
    const trimmed = label.trim();
    if (!trimmed || draft.exclusions.includes(trimmed)) return;
    setDraft({ ...draft, exclusions: [...draft.exclusions, trimmed] });
  };

  const removeExclusion = (label: string) =>
    setDraft({ ...draft, exclusions: draft.exclusions.filter((e) => e !== label) });

  const onSave = async () => {
    await update.mutateAsync(draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="pb-32">
      <header className="mb-12">
        <h1 className="text-4xl font-semibold tracking-tight mb-3">
          Preferences
        </h1>
        <p className="text-muted">
          Shape what your podcast covers and how it sounds.
        </p>
      </header>

      <div className="space-y-12">
        <Section
            title="Topics"
            desc="Pick what you want to hear about. Add custom ones below."
            >
            <div className="flex flex-wrap gap-2 mb-6">
                {/* Preset chips */}
                {PRESET_TOPICS.map((topic) => {
                const active = !!draft.interests.find((i) => i.label === topic);
                return (
                    <button
                    key={topic}
                    onClick={() => toggleTopic(topic)}
                    className={cn("chip", active ? "chip-active" : "chip-default")}
                    >
                    {active && <Check size={12} strokeWidth={3} />}
                    {topic}
                    </button>
                );
                })}

                {/* Custom interests — also rendered as active chips with a remove X */}
                {draft.interests
                .filter((i) => !PRESET_TOPICS.includes(i.label))
                .map((i) => (
                    <span key={i.label} className="chip chip-active group">
                    <Check size={12} strokeWidth={3} />
                    {i.label}
                    <button
                        onClick={() => removeInterest(i.label)}
                        className="ml-1 opacity-70 hover:opacity-100"
                    >
                        <X size={12} />
                    </button>
                    </span>
                ))}
            </div>

            <InlineInput placeholder="Add custom topic…" onAdd={addCustom} />
        </Section>

        <Section
          title="Don't include"
          desc="Topics or angles you'd rather skip."
        >
          <div className="space-y-3">
            {draft.exclusions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {draft.exclusions.map((e) => (
                  <RemovableChip
                    key={e}
                    label={e}
                    red
                    onRemove={() => removeExclusion(e)}
                  />
                ))}
              </div>
            )}
            <InlineInput
              placeholder="e.g. celebrity gossip…"
              onAdd={addExclusion}
            />
          </div>
        </Section>

        <Section
          title="Schedule"
          desc="When should we generate a fresh episode?"
        >
          <div className="flex flex-wrap items-center gap-4">
            <SegmentedControl
              options={[
                { value: "on_demand", label: "On demand" },
                { value: "daily", label: "Daily" },
                { value: "weekly", label: "Weekly" },
              ]}
              value={draft.schedule.type}
              onChange={(v) =>
                setDraft({
                  ...draft,
                  schedule: {
                    ...draft.schedule,
                    type: v as "on_demand" | "daily" | "weekly",
                  },
                })
              }
            />

            {draft.schedule.type !== "on_demand" && (
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={draft.schedule.hour ?? 7}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      schedule: {
                        ...draft.schedule,
                        hour: Number(e.target.value),
                      },
                    })
                  }
                  className="input w-16 text-center font-mono"
                />
                <span className="text-muted">:</span>
                <input
                  type="number"
                  min={0}
                  max={59}
                  value={draft.schedule.minute ?? 0}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      schedule: {
                        ...draft.schedule,
                        minute: Number(e.target.value),
                      },
                    })
                  }
                  className="input w-16 text-center font-mono"
                />
                <span className="text-xs text-muted ml-2">
                  {draft.schedule.tz}
                </span>
              </div>
            )}
          </div>

          {draft.schedule.type === "weekly" && (
            <div className="mt-4">
              <select
                value={draft.schedule.weekday ?? 0}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    schedule: {
                      ...draft.schedule,
                      weekday: Number(e.target.value),
                    },
                  })
                }
                className="input max-w-xs"
              >
                <option value={0}>Monday</option>
                <option value={1}>Tuesday</option>
                <option value={2}>Wednesday</option>
                <option value={3}>Thursday</option>
                <option value={4}>Friday</option>
                <option value={5}>Saturday</option>
                <option value={6}>Sunday</option>
              </select>
            </div>
          )}
        </Section>

        <Section title="Length" desc="Approximate episode duration.">
          <div className="grid grid-cols-3 gap-3 max-w-xl">
            {LENGTHS.map((l) => (
              <SelectableCard
                key={l.value}
                selected={draft.length_min === l.value}
                onClick={() => setDraft({ ...draft, length_min: l.value })}
                title={l.label}
                subtitle={l.desc}
              />
            ))}
          </div>
        </Section>

        <Section title="Tone" desc="How the host should speak.">
          <SegmentedControl
            options={TONES.map((t) => ({ value: t.value, label: t.label }))}
            value={draft.tone}
            onChange={(v) => setDraft({ ...draft, tone: v as Preferences["tone"] })}
          />
        </Section>

        <Section title="Voice" desc="The narrator.">
          <div className="grid grid-cols-2 gap-3 max-w-xl">
            {VOICES.map((v) => (
              <SelectableCard
                key={v.id}
                selected={draft.voice_id === v.id}
                onClick={() => setDraft({ ...draft, voice_id: v.id })}
                title={v.name}
                subtitle={v.desc}
              />
            ))}
          </div>
        </Section>
      </div>

      {/* Sticky save bar */}
      <div className="fixed bottom-0 left-56 right-0 bg-bg/90 backdrop-blur-md border-t border-border z-50">
        <div className="max-w-content mx-auto px-12 py-4 flex items-center justify-between">
          <div className="text-xs text-muted">
            {saved ? (
              <span className="text-accent flex items-center gap-1.5">
                <Check size={14} strokeWidth={3} /> Saved
              </span>
            ) : (
              "Changes are not saved automatically"
            )}
          </div>
          <button
            onClick={onSave}
            disabled={update.isPending}
            className="btn-primary"
          >
            {update.isPending ? "Saving…" : "Save preferences"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  desc,
  children,
}: {
  title: string;
  desc: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="section-title">{title}</h2>
      <p className="section-desc mb-5">{desc}</p>
      {children}
    </section>
  );
}

function RemovableChip({
  label,
  onRemove,
  red,
}: {
  label: string;
  onRemove: () => void;
  red?: boolean;
}) {
  return (
    <span className={cn("chip", red ? "chip-exclude" : "chip-default")}>
      {label}
      <button
        onClick={onRemove}
        className="opacity-50 hover:opacity-100 ml-0.5"
      >
        <X size={12} />
      </button>
    </span>
  );
}

function InlineInput({
  placeholder,
  onAdd,
}: {
  placeholder: string;
  onAdd: (label: string) => void;
}) {
  const [val, setVal] = useState("");
  const submit = () => {
    onAdd(val);
    setVal("");
  };
  return (
    <div className="flex gap-2 max-w-md">
      <input
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder={placeholder}
        className="input flex-1"
      />
      <button
        onClick={submit}
        className="px-3 py-2 border border-border rounded-lg text-sm text-muted hover:text-text hover:border-border-strong transition"
      >
        <Plus size={14} />
      </button>
    </div>
  );
}

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex p-1 bg-surface border border-border rounded-lg">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "px-4 py-1.5 rounded-md text-sm transition duration-150",
            value === o.value
              ? "bg-accent text-white shadow-sm"
              : "text-muted hover:text-text"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function SelectableCard({
  selected,
  onClick,
  title,
  subtitle,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "text-left rounded-xl border p-4 transition duration-150",
        selected
          ? "border-accent bg-accent/5 shadow-[0_0_0_3px_rgb(var(--accent)/0.1)]"
          : "border-border bg-surface hover:border-border-strong"
      )}
    >
      <div className="text-sm font-medium">{title}</div>
      <div className="text-xs text-muted mt-1">{subtitle}</div>
    </button>
  );
}