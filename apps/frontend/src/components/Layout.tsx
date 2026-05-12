import { Link, NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Headphones, Settings, BarChart3, Mic } from "lucide-react";

const navItem = ({ isActive }: { isActive: boolean }) =>
  cn(
    "group flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition duration-150 relative",
    isActive
      ? "text-text font-medium"
      : "text-muted hover:text-text"
  );

export function Layout() {
  return (
    <div className="min-h-full flex">
      <aside className="w-56 border-r border-border flex flex-col bg-bg shrink-0">
        <div className="p-5 pb-8">
          <Link
            to="/"
            className="flex items-center gap-2 text-base font-semibold tracking-tight"
          >
            <span className="w-7 h-7 rounded-md bg-accent/10 flex items-center justify-center">
              <Mic size={14} className="text-accent" strokeWidth={2.5} />
            </span>
            <span>Podcast Gen</span>
          </Link>
        </div>

        <nav className="flex flex-col gap-0.5 px-3 flex-1">
          <NavLink to="/library" end className={navItem}>
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 bg-accent rounded-r" />
                )}
                <Headphones size={15} />
                <span>Library</span>
              </>
            )}
          </NavLink>
          <NavLink to="/preferences" className={navItem}>
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 bg-accent rounded-r" />
                )}
                <Settings size={15} />
                <span>Preferences</span>
              </>
            )}
          </NavLink>
          <NavLink to="/admin" className={navItem}>
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 bg-accent rounded-r" />
                )}
                <BarChart3 size={15} />
                <span>Admin</span>
              </>
            )}
          </NavLink>
        </nav>

        <div className="p-5 pt-3 text-xs text-muted/60">
          v0.1 · demo
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto bg-bg relative">
        {/* Aurora gradient header */}
        <div className="absolute inset-x-0 top-0 h-80 header-gradient pointer-events-none" />

        <div className="max-w-content mx-auto px-12 py-16 relative">
          <Outlet />
        </div>
      </main>
    </div>
  );
}