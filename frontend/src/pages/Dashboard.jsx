import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Card, ScoreRing, SeverityBadge, Spinner, Stat } from "../components/ui";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="text-sm text-red-600">{error}</div>;
  if (!data) return <Spinner />;

  const issues = data.issues_by_severity || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
          <p className="text-sm text-slate-500">Overview across all your websites</p>
        </div>
        <Link to="/websites" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          Add Website
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Websites" value={data.websites} />
        <Stat label="Pages" value={data.total_pages} />
        <Stat label="Open Tasks" value={data.open_tasks} />
        <Stat label="Keywords" value={data.keywords} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="flex items-center justify-center gap-6 p-6">
          <ScoreRing value={data.average_seo_score} size={120} />
          <div>
            <div className="text-sm font-semibold text-slate-700">Avg SEO Score</div>
            <div className="mt-1 text-xs text-slate-400">
              {data.average_seo_score === null ? "No audits yet — run a crawl on a website" : "Weighted across dimensions"}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
              <div className="text-slate-500">Ranked</div>
              <div className="font-semibold">{data.ranking_keywords}</div>
              <div className="text-slate-500">Avg Pos</div>
              <div className="font-semibold">{data.average_position ?? "—"}</div>
              <div className="text-slate-500">Clicks</div>
              <div className="font-semibold">{data.organic_clicks ?? "—"}</div>
              <div className="text-slate-500">Impr.</div>
              <div className="font-semibold">{data.impressions ?? "—"}</div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Issues by severity</h2>
          {Object.keys(issues).length === 0 ? (
            <p className="text-sm text-slate-400">No issues yet.</p>
          ) : (
            <div className="space-y-2">
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) =>
                issues[sev] ? (
                  <div key={sev} className="flex items-center justify-between">
                    <SeverityBadge severity={sev} />
                    <span className="font-semibold text-slate-700">{issues[sev]}</span>
                  </div>
                ) : null,
              )}
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Score trend</h2>
          {data.score_trend.length === 0 ? (
            <p className="text-sm text-slate-400">No audit history yet.</p>
          ) : (
            <div className="flex h-32 items-end gap-2">
              {data.score_trend.map((t) => (
                <div key={t.date} className="flex flex-1 flex-col items-center gap-1">
                  <span className="text-xs font-semibold text-slate-600">{t.score}</span>
                  <div
                    className="w-full rounded-t bg-blue-500"
                    style={{ height: `${t.score}px` }}
                    title={`${t.date}: ${t.score}`}
                  />
                  <span className="text-[10px] text-slate-400">{t.date.slice(5)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <div className="border-b border-slate-100 px-6 py-4">
          <h2 className="text-sm font-semibold text-slate-700">Recent tasks</h2>
        </div>
        {data.recent_tasks.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-400">No tasks yet — run an audit and generate tasks.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.recent_tasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between px-6 py-3">
                <div>
                  <div className="text-sm font-medium text-slate-700">{t.title}</div>
                  <div className="text-xs text-slate-400">{t.status}</div>
                </div>
                <SeverityBadge severity={t.priority} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
