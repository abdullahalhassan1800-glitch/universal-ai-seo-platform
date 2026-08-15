import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Alert, Button, Card, Spinner, Textarea } from "../components/ui";

export default function Keywords() {
  const [websites, setWebsites] = useState([]);
  const [websiteId, setWebsiteId] = useState("");
  const [keywords, setKeywords] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
    Promise.all([
      api.get(`/api/websites/${websiteId}/keywords`),
      api.get(`/api/websites/${websiteId}/clusters`),
    ])
      .then(([kw, cl]) => {
        setKeywords(kw);
        setClusters(cl);
      })
      .catch((e) => setError(e.message));
  }, [websiteId]);

  const addKeywords = async () => {
    const list = input.split("\n").map((s) => s.trim()).filter(Boolean);
    if (!websiteId || list.length === 0) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.post(`/api/websites/${websiteId}/keywords`, { keywords: list });
      setKeywords([...keywords, ...created]);
      setInput("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const buildClusters = async () => {
    if (!websiteId) return;
    setBusy(true);
    setError("");
    try {
      const cl = await api.post(`/api/websites/${websiteId}/clusters`, { keywords: null });
      setClusters(cl);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const removeKeyword = async (id) => {
    try {
      await api.delete(`/api/websites/${websiteId}/keywords/${id}`);
      setKeywords(keywords.filter((k) => k.id !== id));
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Keywords</h1>
          <p className="text-sm text-slate-500">Track keywords and build topic clusters</p>
        </div>
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
      </div>

      {error ? <Alert>{error}</Alert> : null}

      {!websiteId ? (
        <Card className="p-10 text-center text-sm text-slate-400">
          Select a website to manage keywords.
        </Card>
      ) : (
        <>
          <Card className="p-6">
            <h2 className="mb-3 text-sm font-semibold text-slate-700">Add keywords</h2>
            <Textarea
              rows={4}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={"One keyword per line:\nbest seo tool\nbuy seo tool"}
            />
            <Button onClick={addKeywords} disabled={busy} className="mt-3">
              {busy ? "Adding…" : "Add Keywords"}
            </Button>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <div className="border-b border-slate-100 px-6 py-4">
                <h2 className="text-sm font-semibold text-slate-700">Tracked keywords ({keywords.length})</h2>
              </div>
              {keywords.length === 0 ? (
                <p className="px-6 py-4 text-sm text-slate-400">No keywords yet.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {keywords.map((k) => (
                    <li key={k.id} className="flex items-center justify-between px-6 py-3">
                      <div>
                        <div className="text-sm font-medium text-slate-700">{k.keyword}</div>
                        <div className="text-xs text-slate-400">
                          Intent: {k.intent || "—"}
                          {k.volume != null ? ` · Vol: ${k.volume}` : ""}
                          {k.difficulty != null ? ` · Diff: ${k.difficulty}` : ""}
                        </div>
                      </div>
                      <button
                        onClick={() => removeKeyword(k.id)}
                        className="text-sm text-red-500 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                <h2 className="text-sm font-semibold text-slate-700">Topic clusters ({clusters.length})</h2>
                <Button onClick={buildClusters} disabled={busy} className="bg-slate-700 px-3 py-1.5 text-xs hover:bg-slate-800">
                  Build Clusters
                </Button>
              </div>
              {clusters.length === 0 ? (
                <p className="px-6 py-4 text-sm text-slate-400">No clusters yet.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {clusters.map((c) => (
                    <li key={c.id} className="px-6 py-3">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-800">{c.name}</span>
                        {c.intent ? <span className="text-xs text-slate-400">{c.intent}</span> : null}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{c.topic}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(c.keywords || []).map((k) => (
                          <span key={k} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                            {k}
                          </span>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
