export function Card({ className = "", children }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function Stat({ label, value, sub }) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-800">{value ?? "—"}</div>
      {sub ? <div className="mt-1 text-xs text-slate-400">{sub}</div> : null}
    </Card>
  );
}

const SEVERITY_STYLES = {
  CRITICAL: "bg-red-100 text-red-700",
  HIGH: "bg-orange-100 text-orange-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-slate-100 text-slate-600",
};

export function SeverityBadge({ severity }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.LOW}`}>
      {severity}
    </span>
  );
}

export function ScoreRing({ value, size = 96 }) {
  const v = value ?? 0;
  const r = size / 2 - 8;
  const c = 2 * Math.PI * r;
  const offset = c - (v / 100) * c;
  const color = v >= 80 ? "#10b981" : v >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute text-2xl font-bold text-slate-800">{value === null ? "—" : value}</div>
    </div>
  );
}

export function Spinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
    </div>
  );
}

export function Button({ className = "", ...props }) {
  return (
    <button
      className={`rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 ${className}`}
      {...props}
    />
  );
}

export function Textarea({ className = "", ...props }) {
  return (
    <textarea
      className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 ${className}`}
      {...props}
    />
  );
}

export function Alert({ kind = "error", children }) {
  const styles =
    kind === "success"
      ? "border-green-200 bg-green-50 text-green-700"
      : "border-red-200 bg-red-50 text-red-700";
  return <div className={`rounded-lg border px-4 py-3 text-sm ${styles}`}>{children}</div>;
}
