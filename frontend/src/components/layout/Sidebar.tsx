import { NavLink } from "react-router-dom";
import { ClipboardList, FolderOpen, Upload, LogOut } from "lucide-react";

const navItems = [
  { label: "Audit Log", icon: ClipboardList, to: "/audit" },
  { label: "Document Registry", icon: FolderOpen, to: "/documents" },
  { label: "Ingest Document", icon: Upload, to: "/ingest" },
];

export default function Sidebar({ onLogout }: { onLogout: () => void }) {
  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-sidebar border-r border-sidebar-border flex flex-col">
      <div className="h-16 flex items-center px-4 border-b border-sidebar-border">
        <span className="text-2xl font-semibold text-sidebar-foreground">CopInvest</span>
      </div>
      <nav className="flex-1 py-2">
        {navItems.map(({ label, icon: Icon, to }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 h-11 px-4 text-sm transition-colors",
                isActive
                  ? "border-l-[3px] border-sidebar-primary text-sidebar-primary bg-sidebar-accent"
                  : "text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground border-l-[3px] border-transparent",
              ].join(" ")
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <button
        onClick={onLogout}
        className="flex items-center gap-3 h-11 px-4 text-sm text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors border-t border-sidebar-border"
      >
        <LogOut className="h-4 w-4 shrink-0" />
        <span>Sign out</span>
      </button>
    </aside>
  );
}
