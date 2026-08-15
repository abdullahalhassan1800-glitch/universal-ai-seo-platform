import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Alert, Button, Card, SeverityBadge, Spinner } from "../components/ui";

export default function Tasks() {
  const [websites, setWebsites] = useState([]);
  const [websiteId, setWebsiteId] = useState("");
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/websites")
      .then((sites) => {
        setWebsites(sites);
        if (sites.length) setWebsiteId(sites[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!websiteId) return;
    api
      .get(`/api/websites/${websiteId}/tasks`)
      .then(setTasks)
      .catch((e) => setError(e.message));
  }, [websiteId]);

  const updateStatus = async (task, status) => {
    try {
      const updated = await api.patch(`/api/websites/${websiteId}/tasks/${task.id}`, { status });
      setTasks(tasks.map((t) => (t.id === task.id ? updated : t)));
    } catch (e) {
      setError(e.message);
    }
  };

  const prioritize = async () => {
    setError("");
    try {
      const ordered = await api.post(`/api/websites/${websiteId}/tasks/prioritize`);
      setTasks(ordered);
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Tasks</h1>
          <p className="text-sm text-slate-500">AI-prioritized SEO action plan</p>
        </div>
        <div className="flex gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Website</label>
            <select
              value={websiteId}
              onChange={(e) => setWebsiteId(e.target.value)}
              className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select…</option>
              {websites.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
          <Button onClick={prioritize} disabled={!websiteId} className="bg-slate-700 hover:bg-slate-800">
            AI Prioritize
          </Button>
        </div>
      </div>

      {error ? <Alert>{error}</Alert> : null}

      {!websiteId ? (
        <Card className="p-10 text-center text-sm text-slate-400">Select a website to view tasks.</Card>
      ) : tasks.length === 0 ? (
        <Card className="p-10 text-center text-sm text-slate-400">
          No tasks yet. Run an audit and click "Generate Tasks".
        </Card>
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-start justify-between gap-4 px-6 py-4">
                <div>
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={t.priority} />
                    <span className="font-medium text-slate-800">{t.title}</span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{t.status}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{t.description}</p>
                  <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-400">
                    {t.impact != null ? <span>Impact: {t.impact}</span> : null}
                    {t.difficulty != null ? <span>Difficulty: {t.difficulty}</span> : null}
                    {t.urgency != null ? <span>Urgency: {t.urgency}</span> : null}
                    {t.confidence != null ? <span>Confidence: {t.confidence}</span> : null}
                  </div>
                  {t.ai_solution ? (
                    <p className="mt-1 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700">{t.ai_solution}</p>
                  ) : null}
                </div>
                <div className="flex shrink-0 gap-1">
                  {t.status === "pending" ? (
                    <>
                      <button onClick={() => updateStatus(t, "approved")} className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50">
                        Approve
                      </button>
                      <button onClick={() => updateStatus(t, "rejected")} className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">
                        Reject
                      </button>
                    </>
                  ) : null}
                  {t.status !== "completed" ? (
                    <button onClick={() => updateStatus(t, "completed")} className="rounded px-2 py-1 text-xs font-medium text-green-600 hover:bg-green-50">
                      Done
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
