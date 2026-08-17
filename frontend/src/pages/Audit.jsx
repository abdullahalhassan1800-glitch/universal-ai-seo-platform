import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { Alert, Button, Card, ScoreRing, SeverityBadge, Spinner } from "../components/ui";

function ProgressBar({ current, total, status }) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  const isActive = status === "queued" || status === "running";
  return (
    <Card className="overflow-hidden border-blue-100">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4">
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center gap-3">
            {isActive && (
              <span className="relative flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
              </span>
            )}
            <span className="text-sm font-semibold">
              {status === "queued" && "Queued — waiting to start..."}
              {status === "running" && `Crawling... ${current} of ${total} pages`}
              {status === "completed" && `Crawl complete — ${current} pages crawled`}
              {status === "failed" && "Crawl failed"}
            </span>
          </div>
          <span className="text-2xl font-bold">{pct}%</span>
        </div>
      </div>
      <div className="h-3 bg-slate-100">
        <div
          className={`h-full transition-all duration-500 ease-out ${
            status === "failed"
              ? "bg-red-500"
              : status === "completed"
              ? "bg-emerald-500"
              : "bg-gradient-to-r from-blue-500 to-indigo-500"
          } ${isActive ? "animate-pulse" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {isActive && (
        <div className="px-6 py-3 bg-blue-50/50 flex items-center gap-2">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="inline-block h-2 w-2 rounded-full bg-blue-400"
                style={{ animation: `bounce 1.4s infinite ${i * 0.16}s` }}
              />
            ))}
          </div>
          <span className="text-xs text-blue-600">
            Analyzing pages and detecting SEO issues...
          </span>
        </div>
      )}
    </Card>
  );
}

function DimensionBar({ label, value, max = 100 }) {
  const pct = value != null ? Math.min(100, Math.max(0, value)) : 0;
  const color =
    pct >= 80 ? "#16a34a" : pct >= 60 ? "#ca8a04" : pct >= 40 ? "#ea580c" : "#dc2626";
  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-600 capitalize">
          {label.replace(/_/g, " ")}
        </span>
        <span className="text-xs font-bold" style={{ color }}>
          {value != null ? value : "—"}
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function Audit() {
  const [params] = useSearchParams();
  const [websites, setWebsites] = useState([]);
  const [websiteId, setWebsiteId] = useState(params.get("website") || "");
  const [job, setJob] = useState(null);
  const [score, setScore] = useState(null);
  const [issues, setIssues] = useState([]);
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [crawling, setCrawling] = useState(false);
  const pollRef = useRef(null);

  const loadWebsites = useCallback(async () => {
    try {
      const sites = await api.get("/api/websites");
      setWebsites(sites);
      if (sites.length && !websiteId) setWebsiteId(sites[0].id);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [websiteId]);

  const loadData = useCallback(async () => {
    if (!websiteId) return;
    try {
      const [jobData, scoreData, issuesData, pagesData] = await Promise.all([
        api.get(`/api/websites/${websiteId}/crawl/latest`).catch(() => null),
        api.get(`/api/websites/${websiteId}/score`).catch(() => null),
        api.get(`/api/websites/${websiteId}/issues`).catch(() => []),
        api.get(`/api/websites/${websiteId}/pages`).catch(() => []),
      ]);
      setJob(jobData);
      setScore(scoreData);
      setIssues(issuesData);
      setPages(pagesData);
      if (jobData && (jobData.status === "queued" || jobData.status === "running")) {
        startPolling(jobData.id);
      }
    } catch (e) {
      setError(e.message);
    }
  }, [websiteId]);

  const startPolling = (jobId) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      if (!websiteId) return;
      try {
        const j = await api.get(`/api/websites/${websiteId}/crawl/jobs/${jobId}`);
        setJob(j);
        if (j.status === "completed" || j.status === "failed") {
          stopPolling();
          await loadData();
        }
      } catch {
        stopPolling();
      }
    }, 2000);
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => {
    loadWebsites();
    return stopPolling;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (websiteId) loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [websiteId]);

  const startCrawl = async () => {
    if (!websiteId) return;
    setError("");
    setCrawling(true);
    try {
      const j = await api.post(`/api/websites/${websiteId}/crawl`, { max_pages: 100, delay: 0.5 });
      setJob(j);
      startPolling(j.id);
    } catch (e) {
      setError(e.message);
    } finally {
      setCrawling(false);
    }
  };

  const generateTasks = async () => {
    if (!websiteId) return;
    try {
      await api.post(`/api/websites/${websiteId}/issues/generate-tasks`);
      alert("Tasks generated from issues.");
    } catch (e) {
      setError(e.message);
    }
  };

  const downloadReport = () => {
    if (!websiteId) return;
    const token = localStorage.getItem("token") || "";
    const url = `${api._baseUrl || ""}/api/websites/${websiteId}/report`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error("Report generation failed");
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `seo-report-${websiteId}.html`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch((e) => setError(e.message));
  };

  const viewReport = () => {
    if (!websiteId) return;
    const token = localStorage.getItem("token") || "";
    const url = `${api._baseUrl || ""}/api/websites/${websiteId}/report?token=${token}`;
    window.open(url, "_blank");
  };

  if (loading) return <Spinner />;

  const isRunning = job && ["queued", "running"].includes(job.status);
  const dims = score?.dimensions || {};
  const dimEntries = Object.entries(dims).filter(([, v]) => v != null);

  return (
    <div className="space-y-6">
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
      `}</style>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Audit</h1>
          <p className="text-sm text-slate-500">Crawl a website and review technical SEO findings</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Website</label>
            <select
              value={websiteId}
              onChange={(e) => setWebsiteId(e.target.value)}
              className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select...</option>
              {websites.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.domain})
                </option>
              ))}
            </select>
          </div>
          <Button onClick={startCrawl} disabled={!websiteId || isRunning || crawling}>
            {isRunning ? "Crawling..." : "Start Crawl"}
          </Button>
          <Button onClick={generateTasks} disabled={!websiteId} className="bg-slate-700 hover:bg-slate-800">
            Generate Tasks
          </Button>
          <Button onClick={viewReport} disabled={!websiteId || !score} className="bg-blue-600 hover:bg-blue-700">
            View Report
          </Button>
          <Button onClick={downloadReport} disabled={!websiteId || !score} className="bg-emerald-600 hover:bg-emerald-700">
            Download Report
          </Button>
        </div>
      </div>

      {error ? <Alert>{error}</Alert> : null}
      {job && job.status === "failed" ? (
        <Alert>
          Crawl failed: {(job.errors || []).join(" ")}
        </Alert>
      ) : null}

      {!websiteId ? (
        <Card className="p-10 text-center text-sm text-slate-400">
          Select a website to begin an audit.
        </Card>
      ) : (
        <>
          {isRunning ? (
            <ProgressBar
              current={job?.pages_crawled || 0}
              total={job?.max_pages || 100}
              status={job?.status}
            />
          ) : null}

          {job && job.status === "completed" ? (
            <ProgressBar
              current={job.pages_crawled || 0}
              total={job.max_pages || 100}
              status="completed"
            />
          ) : null}

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="flex items-center gap-6 p-6">
              <ScoreRing value={score?.universal_seo_score ?? null} size={100} />
              <div>
                <div className="text-sm font-semibold text-slate-700">Universal SEO Score</div>
                <div className="mt-1 text-xs text-slate-400">
                  {job ? `${job.pages_crawled} pages crawled` : "No audit yet"}
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <h2 className="mb-3 text-sm font-semibold text-slate-700">Issues</h2>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-500">Total</div>
                <div className="font-semibold">{issues.length}</div>
                {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                  <div key={sev}>
                    <SeverityBadge severity={sev} />
                  </div>
                ))}
                {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                  <div key={sev} className="font-semibold">
                    {issues.filter((i) => i.severity === sev).length}
                  </div>
                ))}
              </div>
            </Card>
            <Card className="p-6">
              <h2 className="mb-3 text-sm font-semibold text-slate-700">Dimension Scores</h2>
              <div className="space-y-0">
                {dimEntries.length > 0 ? (
                  dimEntries.map(([k, v]) => (
                    <DimensionBar key={k} label={k} value={v} />
                  ))
                ) : (
                  <p className="text-sm text-slate-400">No scores yet.</p>
                )}
              </div>
            </Card>
          </div>

          <Card>
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="text-sm font-semibold text-slate-700">SEO Issues ({issues.length})</h2>
            </div>
            {issues.length === 0 ? (
              <p className="px-6 py-4 text-sm text-slate-400">
                {job ? "No issues found. Great job!" : "Run a crawl to detect issues."}
              </p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {issues.map((i) => (
                  <li key={i.id} className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={i.severity} />
                      <span className="font-medium text-slate-800">{i.issue}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{i.explanation}</p>
                    {i.recommendation ? (
                      <p className="mt-1 text-xs text-slate-400">Fix: {i.recommendation}</p>
                    ) : null}
                    {i.ai_solution ? (
                      <p className="mt-1 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700">{i.ai_solution}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="text-sm font-semibold text-slate-700">Pages ({pages.length})</h2>
            </div>
            {pages.length === 0 ? (
              <p className="px-6 py-4 text-sm text-slate-400">No pages crawled yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {pages.map((p) => (
                  <li key={p.id} className="flex items-center justify-between px-6 py-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-slate-700">{p.url}</div>
                      <div className="text-xs text-slate-400">
                        {p.title || "No title"} · {p.word_count} words
                      </div>
                    </div>
                    <span
                      className={`ml-3 rounded px-2 py-0.5 text-xs font-semibold ${
                        p.status_code === 200 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {p.status_code}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
