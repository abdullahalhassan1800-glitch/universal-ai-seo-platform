import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Alert, Button, Card, Input, Spinner } from "../components/ui";

export default function Websites() {
  const [websites, setWebsites] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [sites, proj] = await Promise.all([api.get("/api/websites"), api.get("/api/projects")]);
      setWebsites(sites);
      setProjects(proj);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createProject = async () => {
    if (!projectName.trim()) return;
    try {
      const p = await api.post("/api/projects", { name: projectName });
      setProjects([...projects, p]);
      setProjectId(p.id);
      setProjectName("");
    } catch (e) {
      setError(e.message);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const w = await api.post("/api/websites", {
        name,
        domain,
        project_id: projectId || null,
      });
      setWebsites([w, ...websites]);
      setName("");
      setDomain("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/api/websites/${id}`);
      setWebsites(websites.filter((w) => w.id !== id));
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Websites</h1>
        <p className="text-sm text-slate-500">Add domains to crawl and audit</p>
      </div>

      {error ? <Alert>{error}</Alert> : null}

      <Card className="p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-700">Add a website</h2>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Name</label>
              <Input required value={name} onChange={(e) => setName(e.target.value)} placeholder="My Website" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Domain</label>
              <Input required value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-slate-700">Project (optional)</label>
              <div className="flex gap-2">
                <select
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">— None —</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <Input
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="New project"
                  className="w-40"
                />
                <Button type="button" onClick={createProject} className="bg-slate-700 hover:bg-slate-800">
                  Add
                </Button>
              </div>
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Adding…" : "Add Website"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <div className="border-b border-slate-100 px-6 py-4">
          <h2 className="text-sm font-semibold text-slate-700">Your websites ({websites.length})</h2>
        </div>
        {websites.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-400">No websites yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {websites.map((w) => (
              <li key={w.id} className="flex items-center justify-between px-6 py-4">
                <div>
                  <div className="font-medium text-slate-800">{w.name}</div>
                  <div className="text-sm text-slate-500">{w.domain}</div>
                  <div className="mt-1 text-xs text-slate-400">
                    {w.last_crawl_at ? `Last crawl: ${new Date(w.last_crawl_at).toLocaleString()}` : "Not crawled yet"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <a
                    href={`/audit?website=${w.id}`}
                    className="rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
                  >
                    Audit
                  </a>
                  <button
                    onClick={() => remove(w.id)}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
