import { NavLink } from "react-router-dom";
import { ClipboardList, FolderOpen, Upload } from "lucide-react";

const navItems = [
  { label: "Audit Log", icon: ClipboardList, to: "/audit" },
  { label: "Document Registry", icon: FolderOpen, to: "/documents" },
  { label: "Ingest Document", icon: Upload, to: "/ingest" },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-neutral-900 border-r border-neutral-800 flex flex-col">
      <div className="h-16 flex items-center px-4 border-b border-neutral-800">
        <span className="text-2xl font-semibold text-white">CopInvest</span>
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
                  ? "border-l-[3px] border-indigo-500 text-indigo-500 bg-neutral-800"
                  : "text-neutral-400 hover:bg-neutral-800 hover:text-white border-l-[3px] border-transparent",
              ].join(" ")
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
