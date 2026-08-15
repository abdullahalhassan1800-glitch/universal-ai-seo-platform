import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Alert, Card, Spinner } from "../components/ui";

export default function SearchEngines() {
  const [engines, setEngines] = useState([]);
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get("/api/engines"), api.get("/api/websites")])
      .then(async ([eng, sites]) => {
        setEngines(eng);
        if (sites.length) {
          const conns = await api.get(`/api/websites/${sites[0].id}/connections`);
          setConnections(conns);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  const capLabels = {
    get_keyword_data: "Keyword volume",
    get_ranking_data: "Ranking",
    get_search_visibility: "Visibility",
    get_index_signals: "Index signals",
    analyze_serp: "SERP analysis",
    get_search_analytics: "Analytics",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Search Engines</h1>
        <p className="text-sm text-slate-500">
          Official connectors. Data is only shown when a search engine's API is configured — never fabricated.
        </p>
      </div>

      {error ? <Alert>{error}</Alert> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {engines.map((e) => {
          const conn = connections.find((c) => c.engine_id === e.engine_id);
          return (
            <Card key={e.engine_id} className="p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-slate-800">{e.display_name}</h2>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-semibold ${
                    e.status === "configured"
                      ? "bg-green-100 text-green-700"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {conn?.status || e.status}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-400">{e.reason || "No configuration detected."}</p>
              <div className="mt-3 space-y-1">
                {Object.entries(e.capabilities || {}).map(([cap, enabled]) => (
                  <div key={cap} className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">{capLabels[cap] || cap}</span>
                    <span className={enabled ? "font-semibold text-green-600" : "text-slate-300"}>
                      {enabled ? "Available" : "Unavailable"}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          );
        })}
      </div>

      <p className="text-xs text-slate-400">
        Configure credentials in the backend <code className="rounded bg-slate-100 px-1">.env</code> (GSC, BING_API_KEY,
        BRAVE_API_KEY) to enable live data. See <code className="rounded bg-slate-100 px-1">.env.example</code>.
      </p>
    </div>
  );
}
