import { BarChart3 } from "lucide-react";

export function Admin() {
  return (
    <div>
      <header className="mb-12">
        <h1 className="text-4xl font-semibold tracking-tight mb-3">Admin</h1>
        <p className="text-muted">Usage and pipeline metrics.</p>
      </header>

      <div className="card text-center py-20">
        <BarChart3 size={28} className="text-muted mx-auto mb-4" />
        <div className="text-sm font-medium mb-1">Dashboard coming next</div>
        <div className="text-xs text-muted">
          Real-time metrics from the events table.
        </div>
      </div>
    </div>
  );
}