import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import {
  getFirm, getFirmHoldings, getFirmPeers, refreshFirm, streamInsight,
} from "../api";
import {
  fmtAUM, fmtNum, fmtDate, fmtPct, severityClass, severityDot,
  materialityColor, cn,
} from "../utils";

const TABS = ["Overview", "Changes", "Risk Flags", "Disclosures", "Holdings", "Peers"];
const PIE_COLORS = [
  "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
  "#ef4444", "#ec4899", "#6366f1", "#14b8a6", "#f97316",
];

export default function FirmProfile() {
  const { crd } = useParams();
  const [data, setData] = useState(null);
  const [holdings, setHoldings] = useState(null);
  const [peers, setPeers] = useState(null);
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    setLoading(true);
    getFirm(crd)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [crd]);

  useEffect(() => {
    if (tab === 4 && !holdings) {
      getFirmHoldings(crd).then(setHoldings).catch(() => {});
    }
    if (tab === 5 && !peers) {
      getFirmPeers(crd).then(setPeers).catch(() => {});
    }
  }, [tab, crd, holdings, peers]);

  const handleRefresh = () => {
    setRefreshing(true);
    refreshFirm(crd)
      .then(() => setTimeout(() => {
        getFirm(crd).then(setData);
        setRefreshing(false);
      }, 3000))
      .catch(() => setRefreshing(false));
  };

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>;
  if (!data) return <div className="text-center py-20 text-gray-500">Firm not found</div>;

  const { firm, disclosures, changes, flags, key_persons, holding_snapshot } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <Link to="/" className="text-accent text-sm hover:underline mb-4 inline-block">&larr; Back</Link>

      <header className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              {firm.legal_name || firm.doing_business_as}
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              CRD {firm.crd_number}
              {firm.cik && <> &middot; CIK {firm.cik}</>}
              {firm.city && <> &middot; {firm.city}, {firm.state}</>}
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="bg-panel border border-border rounded-lg px-3 py-1.5 text-xs text-gray-300 hover:border-accent/50 transition disabled:opacity-50"
          >
            {refreshing ? "Refreshing..." : "Refresh Data"}
          </button>
        </div>
      </header>

      <div className="flex gap-1 mb-6 border-b border-border overflow-x-auto">
        {TABS.map((label, i) => (
          <button
            key={label}
            onClick={() => setTab(i)}
            className={cn(
              "px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition",
              tab === i
                ? "border-accent text-white"
                : "border-transparent text-gray-400 hover:text-gray-200"
            )}
          >
            {label}
            {i === 2 && flags.length > 0 && (
              <span className="ml-1.5 bg-red-500/20 text-red-400 text-xs px-1.5 py-0.5 rounded-full">
                {flags.length}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="animate-fade-in">
        {tab === 0 && <OverviewTab firm={firm} changes={changes} flags={flags} keyPersons={key_persons} snapshot={holding_snapshot} crd={crd} />}
        {tab === 1 && <ChangesTab changes={changes} />}
        {tab === 2 && <RiskFlagsTab flags={flags} />}
        {tab === 3 && <DisclosuresTab disclosures={disclosures} />}
        {tab === 4 && <HoldingsTab holdings={holdings} snapshot={holding_snapshot} />}
        {tab === 5 && <PeersTab peers={peers} crd={crd} />}
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-panel border border-border rounded-lg p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function OverviewTab({ firm, changes, flags, keyPersons, snapshot, crd }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="AUM" value={fmtAUM(firm.aum_total)} sub={firm.aum_discretionary ? `${fmtAUM(firm.aum_discretionary)} discretionary` : null} />
        <MetricCard label="Employees" value={fmtNum(firm.employee_count)} sub={firm.employee_count_prior ? `Prior: ${fmtNum(firm.employee_count_prior)}` : null} />
        <MetricCard label="Clients" value={fmtNum(firm.client_count)} />
        <MetricCard label="DRP Count" value={firm.drp_count || 0} sub={firm.has_criminal_drp ? "Includes criminal" : null} />
      </div>

      {snapshot && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="13F Total Value" value={fmtAUM(snapshot.total_value)} />
          <MetricCard label="Positions" value={fmtNum(snapshot.holding_count)} />
          <MetricCard label="Top 10 Concentration" value={fmtPct(snapshot.top10_concentration)} />
          <MetricCard label="Largest Position" value={fmtPct(snapshot.largest_position_pct)} />
        </div>
      )}

      <AIInsightPanel crd={crd} />

      {keyPersons && keyPersons.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-2">Key Personnel</h3>
          <div className="bg-panel border border-border rounded-lg divide-y divide-border">
            {keyPersons.map((p) => (
              <div key={p.id} className="px-4 py-2 flex justify-between text-sm">
                <span className="text-gray-200">{p.full_name}</span>
                <span className="text-gray-500">{p.role}{p.ownership_pct ? ` (${fmtPct(p.ownership_pct)})` : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {changes.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-2">Recent Changes</h3>
          <div className="space-y-2">
            {changes.slice(0, 5).map((c) => (
              <ChangeRow key={c.id} change={c} />
            ))}
          </div>
        </div>
      )}

      {flags.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-2">Active Risk Flags</h3>
          <div className="space-y-2">
            {flags.slice(0, 3).map((f) => (
              <FlagCard key={f.id} flag={f} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AIInsightPanel({ crd }) {
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [done, setDone] = useState(false);

  const start = useCallback(() => {
    setText("");
    setStreaming(true);
    setDone(false);
    const cancel = streamInsight(
      crd,
      (chunk) => setText((prev) => prev + chunk),
      () => { setStreaming(false); setDone(true); },
      () => { setStreaming(false); setDone(true); }
    );
    return cancel;
  }, [crd]);

  return (
    <div className="bg-panel border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">AI Insight</h3>
        <button
          onClick={start}
          disabled={streaming}
          className="bg-accent hover:bg-accent-hover text-white text-xs font-medium px-3 py-1.5 rounded-lg transition disabled:opacity-50"
        >
          {streaming ? "Analyzing..." : done ? "Regenerate" : "Generate Analysis"}
        </button>
      </div>
      {text ? (
        <div className={cn("text-sm text-gray-300 whitespace-pre-wrap leading-relaxed", streaming && "typing-cursor")}>
          {text}
        </div>
      ) : (
        <p className="text-sm text-gray-500">Click &quot;Generate Analysis&quot; for an AI-powered regulatory assessment.</p>
      )}
    </div>
  );
}

function ChangesTab({ changes }) {
  const [filter, setFilter] = useState("all");
  const filtered = filter === "all" ? changes : changes.filter((c) => c.materiality === filter);

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {["all", "HIGH", "MEDIUM", "LOW"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-lg border transition",
              filter === f ? "border-accent text-white bg-accent/10" : "border-border text-gray-400"
            )}
          >
            {f === "all" ? "All" : f}
          </button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">No changes recorded</p>
      ) : (
        <div className="space-y-2">
          {filtered.map((c) => <ChangeRow key={c.id} change={c} />)}
        </div>
      )}
    </div>
  );
}

function ChangeRow({ change }) {
  return (
    <div className="bg-panel border border-border rounded-lg px-4 py-3 text-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-gray-200">{change.field_name}</span>
        <div className="flex items-center gap-2">
          {change.materiality && (
            <span className={cn("text-xs", materialityColor(change.materiality))}>
              {change.materiality}
            </span>
          )}
          <span className="text-xs text-gray-500">{fmtDate(change.created_at)}</span>
        </div>
      </div>
      {change.description && <p className="text-gray-400 text-xs">{change.description}</p>}
      {change.previous_value && (
        <p className="text-xs text-gray-500 mt-1">
          <span className="text-red-400/70">{change.previous_value}</span>
          {" → "}
          <span className="text-emerald-400/70">{change.new_value}</span>
        </p>
      )}
    </div>
  );
}

function RiskFlagsTab({ flags }) {
  if (flags.length === 0) return <p className="text-sm text-gray-500 py-8 text-center">No active risk flags</p>;

  return (
    <div className="space-y-3">
      {flags.map((f) => <FlagCard key={f.id} flag={f} />)}
    </div>
  );
}

function FlagCard({ flag }) {
  return (
    <div className={cn("border rounded-lg px-4 py-3", severityClass(flag.severity))}>
      <div className="flex items-center gap-2 mb-1">
        <span className={cn("w-2 h-2 rounded-full", severityDot(flag.severity))} />
        <span className="text-sm font-semibold">{flag.title}</span>
        <span className="text-xs opacity-70">{flag.severity}</span>
        {flag.category && <span className="text-xs opacity-50 ml-auto">{flag.category}</span>}
      </div>
      {flag.description && <p className="text-xs opacity-80 mb-1">{flag.description}</p>}
      {flag.why_it_matters && (
        <p className="text-xs opacity-60 italic">Why it matters: {flag.why_it_matters}</p>
      )}
      {flag.evidence && (
        <p className="text-xs opacity-50 mt-1">Evidence: {flag.evidence}</p>
      )}
    </div>
  );
}

function DisclosuresTab({ disclosures }) {
  if (disclosures.length === 0) return <p className="text-sm text-gray-500 py-8 text-center">No disclosures on record</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-gray-500 border-b border-border">
          <tr>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Date</th>
            <th className="pb-2 pr-4">Description</th>
            <th className="pb-2 pr-4">Resolution</th>
            <th className="pb-2">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {disclosures.map((d) => (
            <tr key={d.id}>
              <td className="py-2 pr-4 text-gray-300 whitespace-nowrap">{d.disclosure_type || "N/A"}</td>
              <td className="py-2 pr-4 text-gray-400 whitespace-nowrap">{fmtDate(d.event_date)}</td>
              <td className="py-2 pr-4 text-gray-400 max-w-md">{d.description || "N/A"}</td>
              <td className="py-2 pr-4 text-gray-500 max-w-xs">{d.resolution || "-"}</td>
              <td className="py-2">
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full",
                  d.is_resolved ? "bg-emerald-500/20 text-emerald-400" : "bg-yellow-500/20 text-yellow-400"
                )}>
                  {d.is_resolved ? "Resolved" : "Open"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HoldingsTab({ holdings, snapshot }) {
  if (!holdings) return <p className="text-sm text-gray-500 py-8 text-center">Loading holdings...</p>;
  const { holdings: positions } = holdings;
  if (!positions || positions.length === 0) return <p className="text-sm text-gray-500 py-8 text-center">No 13F holdings data available</p>;

  const top10 = positions.slice(0, 10).map((h) => ({
    name: h.ticker || h.issuer_name?.slice(0, 15) || h.cusip,
    value: h.market_value || 0,
  }));

  return (
    <div className="space-y-6">
      {snapshot && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Total Value" value={fmtAUM(snapshot.total_value)} />
          <MetricCard label="Positions" value={fmtNum(snapshot.holding_count)} />
          <MetricCard label="Top 10 Concentration" value={fmtPct(snapshot.top10_concentration)} />
          <MetricCard label="Largest Position" value={fmtPct(snapshot.largest_position_pct)} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-panel border border-border rounded-lg p-4">
          <h4 className="text-sm font-semibold text-white mb-3">Top 10 Holdings</h4>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={top10}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name }) => name}
              >
                {top10.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => fmtAUM(v)} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-panel border border-border rounded-lg p-4">
          <h4 className="text-sm font-semibold text-white mb-3">Holdings by Value</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={top10}>
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={fmtAUM} />
              <Tooltip formatter={(v) => fmtAUM(v)} />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-gray-500 border-b border-border">
            <tr>
              <th className="pb-2 pr-4">Issuer</th>
              <th className="pb-2 pr-4">Ticker</th>
              <th className="pb-2 pr-4">CUSIP</th>
              <th className="pb-2 pr-4 text-right">Value</th>
              <th className="pb-2 pr-4 text-right">Shares</th>
              <th className="pb-2 text-right">Weight</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {positions.map((h) => (
              <tr key={h.id}>
                <td className="py-2 pr-4 text-gray-300">{h.issuer_name || "N/A"}</td>
                <td className="py-2 pr-4 text-gray-400">{h.ticker || "-"}</td>
                <td className="py-2 pr-4 text-gray-500 font-mono text-xs">{h.cusip || "-"}</td>
                <td className="py-2 pr-4 text-right text-gray-300">{fmtAUM(h.market_value)}</td>
                <td className="py-2 pr-4 text-right text-gray-400">{fmtNum(h.shares)}</td>
                <td className="py-2 text-right text-gray-400">{h.weight != null ? `${h.weight.toFixed(2)}%` : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PeersTab({ peers, crd }) {
  if (!peers) return <p className="text-sm text-gray-500 py-8 text-center">Loading peers...</p>;
  const peerList = peers.peers || [];
  if (peerList.length === 0) return <p className="text-sm text-gray-500 py-8 text-center">No peer firms found</p>;

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-gray-500 border-b border-border">
            <tr>
              <th className="pb-2 pr-4">Firm</th>
              <th className="pb-2 pr-4 text-right">AUM</th>
              <th className="pb-2 pr-4 text-right">Employees</th>
              <th className="pb-2 pr-4">Strategy</th>
              <th className="pb-2 pr-4">Location</th>
              <th className="pb-2 pr-4 text-right">Risk Flags</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {peerList.map(({ firm: p, flags: pFlags }) => (
              <tr key={p.crd_number}>
                <td className="py-2 pr-4">
                  <Link to={`/firm/${p.crd_number}`} className="text-accent hover:underline">
                    {p.legal_name || p.doing_business_as}
                  </Link>
                  <p className="text-xs text-gray-500">CRD {p.crd_number}</p>
                </td>
                <td className="py-2 pr-4 text-right text-gray-300">{fmtAUM(p.aum_total)}</td>
                <td className="py-2 pr-4 text-right text-gray-400">{fmtNum(p.employee_count)}</td>
                <td className="py-2 pr-4 text-gray-400">{p.primary_strategy || "-"}</td>
                <td className="py-2 pr-4 text-gray-400">{[p.city, p.state].filter(Boolean).join(", ")}</td>
                <td className="py-2 pr-4 text-right">
                  {pFlags.length > 0 ? (
                    <span className="text-red-400">{pFlags.length}</span>
                  ) : (
                    <span className="text-emerald-400">0</span>
                  )}
                </td>
                <td className="py-2">
                  <Link
                    to={`/compare?firms=${crd},${p.crd_number}`}
                    className="text-xs text-accent hover:underline"
                  >
                    Compare
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
