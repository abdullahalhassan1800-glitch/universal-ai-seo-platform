import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/websites", label: "Websites" },
  { to: "/audit", label: "Audit" },
  { to: "/keywords", label: "Keywords" },
  { to: "/tasks", label: "Tasks" },
  { to: "/engines", label: "Search Engines" },
];

export default function Layout() {
  const { user, workspace, logout } = useAuth();
  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-60 shrink-0 border-r border-slate-200 bg-white">
        <div className="px-4 py-5">
          <h1 className="text-lg font-bold text-slate-800">SEO Platform</h1>
          <p className="mt-0.5 text-xs text-slate-400">{workspace?.name || "Workspace"}</p>
        </div>
        <nav className="flex flex-col gap-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="text-sm text-slate-500">
            {user ? <span className="font-semibold text-slate-700">{user.name || user.email}</span> : null}
          </div>
          <button onClick={logout} className="text-sm font-medium text-slate-500 hover:text-red-600">
            Logout
          </button>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
