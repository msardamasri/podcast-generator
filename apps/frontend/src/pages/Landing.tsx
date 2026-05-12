import { Link } from "react-router-dom";
import { Headphones, Settings, BarChart3, ArrowRight, Mic } from "lucide-react";

export function Landing() {
  return (
    <div className="max-w-3xl mx-auto pt-8">
      {/* Hero */}
      <div className="text-center mb-20">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-surface text-xs text-muted mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          Personal podcast generator
        </div>

        <h1 className="text-5xl font-semibold tracking-tight mb-5">
          News, in your ear.
          <br />
          <span className="text-muted">Tuned to you.</span>
        </h1>

        <p className="text-muted max-w-lg mx-auto mb-10 leading-relaxed">
          Pick what you care about. We pull the latest stories, write a script,
          and turn it into a podcast on the schedule you choose.
        </p>

        <Link
          to="/library"
          className="btn-primary text-base px-6 py-3 inline-flex"
        >
          <Mic size={16} />
          Open library
          <ArrowRight size={16} />
        </Link>
      </div>

      {/* Section cards */}
      <div className="grid grid-cols-3 gap-3">
        <SectionCard
          to="/library"
          icon={<Headphones size={18} />}
          title="Library"
          desc="Listen to past episodes or generate a new one on demand."
        />
        <SectionCard
          to="/preferences"
          icon={<Settings size={18} />}
          title="Preferences"
          desc="Choose topics, tone, voice, and when episodes get generated."
        />
        <SectionCard
          to="/admin"
          icon={<BarChart3 size={18} />}
          title="Admin"
          desc="Real-time usage metrics, pipeline health, and event log."
        />
      </div>

      {/* Footer note */}
      <div className="text-center mt-20 text-xs text-muted/60">
        Built for Prosper AI · OpenAI · ElevenLabs · Firecrawl
      </div>
    </div>
  );
}

function SectionCard({
  to,
  icon,
  title,
  desc,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
}) {
  return (
    <Link
      to={to}
      className="card group hover:border-border-strong hover:bg-surface-elevated transition duration-150"
    >
      <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center text-accent mb-4">
        {icon}
      </div>
      <div className="flex items-center justify-between mb-1">
        <div className="text-sm font-medium">{title}</div>
        <ArrowRight
          size={14}
          className="text-muted opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition"
        />
      </div>
      <div className="text-xs text-muted leading-relaxed">{desc}</div>
    </Link>
  );
}