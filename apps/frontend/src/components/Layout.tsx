import { Link, NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Headphones, Settings, BarChart3 } from "lucide-react";

const navItem = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition",
    isActive ? "bg-surface text-text" : "text-muted hover:text-text"
  );

export function Layout() {
  return (
    <div className="min-h-full flex">
      <aside className="w-56 border-r border-border p-4 flex flex-col gap-1">
        <Link to="/" className="font-semibold mb-6 text-text">
          Podcast Gen
        </Link>
        <NavLink to="/" end className={navItem}>
          <Headphones size={16} /> Library
        </NavLink>
        <NavLink to="/preferences" className={navItem}>
          <Settings size={16} /> Preferences
        </NavLink>
        <NavLink to="/admin" className={navItem}>
          <BarChart3 size={16} /> Admin
        </NavLink>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}