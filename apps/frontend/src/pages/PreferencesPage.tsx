import { useEffect, useState } from "react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { usePreferences, useUpdatePreferences } from "@/hooks/usePreferences";
import type { Interest, Preferences } from "@/api/types";
import { X, Plus } from "lucide-react";

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
  { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel" },
  { id: "pNInz6obpgDQGcFmaJgB", name: "Adam" },
  { id: "nPczCjzI2devNBz1zQrb", name: "Brian" },
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Sarah" },
];

export function PreferencesPage() {
  const { data, isLoading } = usePreferences();
  const update = useUpdatePreferences();
  const [draft, setDraft] = useState<Preferences | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  if (isLoading || !draft) return <div className="text-muted">Loading...</div>;

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
    if (!label.trim()) return;
    if (draft.interests.find((i) => i.label === label)) return;
    setDraft({
      ...draft,
      interests: [...draft.interests, { label: label.trim(), weight: 1.0 }],
    });
  };

  const removeInterest = (label: string) => {
    setDraft({
      ...draft,
      interests: draft.interests.filter((i) => i.label !== label),
    });
  };

  const addExclusion = (label: string) => {
    if (!label.trim() || draft.exclusions.includes(label)) return;
    setDraft({ ...draft, exclusions: [...draft.exclusions, label.trim()] });
  };

  const removeExclusion = (label: string) => {
    setDraft({
      ...draft,
      exclusions: draft.exclusions.filter((e) => e !== label),
    });
  };

  const onSave = () => update.mutate(draft);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Preferences</h1>
        <Button onClick={onSave} disabled={update.isPending}>
          {update.isPending ? "Saving..." : "Save"}
        </Button>
      </div>

      <Card>
        <h2 className="font-medium mb-3">Topics</h2>
        <div className="flex flex-wrap gap-2 mb-4">
          {PRESET_TOPICS.map((topic) => {
            const active = draft.interests.find((i) => i.label === topic);
            return (
              <button
                key={topic}
                onClick={() => toggleTopic(topic)}
                className={`px-3 py-1.5 text-sm rounded-full border transition ${
                  active
                    ? "bg-accent border-accent text-white"
                    : "bg-surface border-border text-muted hover:text-text"
                }`}
              >
                {topic}
              </button>
            );
          })}
        </div>

        <h3 className="text-sm text-muted mb-2">Custom interests</h3>
        <div className="flex flex-wrap gap-2 mb-2">
          {draft.interests
            .filter((i) => !PRESET_TOPICS.includes(i.label))
            .map((i) => (
              <Chip
                key={i.label}
                label={i.label}
                onRemove={() => removeInterest(i.label)}
              />
            ))}
        </div>
        <InlineInput placeholder="Add custom topic..." onAdd={addCustom} />
      </Card>

      <Card>
        <h2 className="font-medium mb-3">Exclude</h2>
        <div className="flex flex-wrap gap-2 mb-2">
          {draft.exclusions.map((e) => (
            <Chip key={e} label={e} onRemove={() => removeExclusion(e)} red />
          ))}
        </div>
        <InlineInput placeholder="Don't include..." onAdd={addExclusion} />
      </Card>
      <Card>
        <h2 className="font-medium mb-3">Schedule</h2>
        <div className="grid grid-cols-4 gap-4">
            <div>
            <label className="text-xs text-muted block mb-1">Frequency</label>
            <select
                value={draft.schedule.type}
                onChange={(e) =>
                setDraft({
                    ...draft,
                    schedule: {
                    ...draft.schedule,
                    type: e.target.value as "on_demand" | "daily" | "weekly",
                    },
                })
                }
                className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
            >
                <option value="on_demand">On demand</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
            </select>
            </div>

            {draft.schedule.type !== "on_demand" && (
            <>
                <div>
                <label className="text-xs text-muted block mb-1">Hour</label>
                <input
                    type="number"
                    min={0}
                    max={23}
                    value={draft.schedule.hour ?? 7}
                    onChange={(e) =>
                    setDraft({
                        ...draft,
                        schedule: { ...draft.schedule, hour: Number(e.target.value) },
                    })
                    }
                    className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
                />
                </div>
                <div>
                <label className="text-xs text-muted block mb-1">Minute</label>
                <input
                    type="number"
                    min={0}
                    max={59}
                    value={draft.schedule.minute ?? 30}
                    onChange={(e) =>
                    setDraft({
                        ...draft,
                        schedule: { ...draft.schedule, minute: Number(e.target.value) },
                    })
                    }
                    className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
                />
                </div>
            </>
            )}

            {draft.schedule.type === "weekly" && (
            <div>
                <label className="text-xs text-muted block mb-1">Day</label>
                <select
                value={draft.schedule.weekday ?? 1}
                onChange={(e) =>
                    setDraft({
                    ...draft,
                    schedule: { ...draft.schedule, weekday: Number(e.target.value) },
                    })
                }
                className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
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
        </div>
        {draft.schedule.type !== "on_demand" && (
            <p className="text-xs text-muted mt-2">
            Timezone: {draft.schedule.tz} · We'll generate a fresh episode at that
            time covering the last 24 hours of news.
            </p>
        )}
      </Card>
      <Card>
        <h2 className="font-medium mb-3">Episode shape</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-muted block mb-1">Length</label>
            <select
              value={draft.length_min}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  length_min: Number(e.target.value) as 5 | 10 | 20,
                })
              }
              className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
            >
              <option value={5}>5 min</option>
              <option value={10}>10 min</option>
              <option value={20}>20 min</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">Tone</label>
            <select
              value={draft.tone}
              onChange={(e) =>
                setDraft({ ...draft, tone: e.target.value as Preferences["tone"] })
              }
              className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
            >
              <option value="conversational">Conversational</option>
              <option value="formal">Formal</option>
              <option value="energetic">Energetic</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">Voice</label>
            <select
              value={draft.voice_id}
              onChange={(e) => setDraft({ ...draft, voice_id: e.target.value })}
              className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
            >
              {VOICES.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>
    </div>
  );
}

function Chip({
  label,
  onRemove,
  red,
}: {
  label: string;
  onRemove: () => void;
  red?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm border ${
        red
          ? "bg-red-950 border-red-900 text-red-200"
          : "bg-surface border-border"
      }`}
    >
      {label}
      <button onClick={onRemove} className="opacity-60 hover:opacity-100">
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
  return (
    <div className="flex gap-2">
      <input
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            onAdd(val);
            setVal("");
          }
        }}
        placeholder={placeholder}
        className="flex-1 bg-bg border border-border rounded px-3 py-1.5 text-sm"
      />
      <button
        onClick={() => {
          onAdd(val);
          setVal("");
        }}
        className="px-3 py-1.5 border border-border rounded text-sm text-muted hover:text-text"
      >
        <Plus size={14} />
      </button>
    </div>
  );
}