import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { getFirm, searchFirms } from "../api";
import { fmtAUM, fmtNum, cn } from "../utils";

export default function Comparison() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [firmData, setFirmData] = useState({});
  const [loading, setLoading] = useState(true);
  const [addQuery, setAddQuery] = useState("");
  const [addResults, setAddResults] = useState([]);

  const crds = (searchParams.get("firms") || "").split(",").filter(Boolean);

  useEffect(() => {
    if (crds.length === 0) { setLoading(false); return; }
    setLoading(true);
    Promise.all(crds.map((crd) => getFirm(crd).then((d) => [crd, d]).catch(() => [crd, null])))
      .then((results) => {
        const map = {};
        results.forEach(([crd, d]) => { if (d) map[crd] = d; });
        setFirmData(map);
      })
      .finally(() => setLoading(false));
  }, [searchParams.get("firms")]);

  function removeFirm(crd) {
    const next = crds.filter((c) => c !== crd);
    setSearchParams({ firms: next.join(",") });
  }

  function addFirm(crd) {
    if (!crds.includes(crd) && crds.length < 5) {
      setSearchParams({ firms: [...crds, crd].join(",") });
    }
    setAddQuery("");
    setAddResults([]);
  }

  function handleAddSearch(q) {
    setAddQuery(q);
    if (q.length >= 2) {
      searchFirms({ q, limit: 5 }).then((d) => setAddResults(d.firms || [])).catch(() => {});
    } else {
      setAddResults([]);
    }
  }

  const entries = crds.map((crd) => firmData[crd]).filter(Boolean);

  const aumData = entries.map((d) => ({
    name: d.firm.legal_name?.slice(0, 15) || d.firm.crd_number,
    AUM: d.firm.aum_total || 0,
  }));

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <Link to="/" className="text-accent text-sm hover:underline mb-4 inline-block">&larr; Back</Link>
      <h1 className="text-2xl font-bold text-white mb-6">Firm Comparison</h1>

      <div className="mb-6 flex gap-3 items-end">
        <div className="relative">
          <input
            type="text"
            placeholder="Add firm..."
            value={addQuery}
            onChange={(e) => handleAddSearch(e.target.value)}
            className="bg-panel border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent w-64"
          />
          {addResults.length > 0 && (
            <div className="absolute top-full mt-1 left-0 right-0 bg-panel border border-border rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
              {addResults.map((f) => (
                <button
                  key={f.crd_number}
                  onClick={() => addFirm(f.crd_number)}
                  disabled={crds.includes(f.crd_number)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-surface transition disabled:opacity-40"
                >
                  {f.legal_name} <span className="text-gray-500 text-xs">CRD {f.crd_number}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <p className="text-xs text-gray-500">{crds.length}/5 firms</p>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">Add firms to compare</p>
      ) : (
        <>
          {aumData.length > 1 && (
            <div className="bg-panel border border-border rounded-lg p-4 mb-6">
              <h3 className="text-sm font-semibold text-white mb-3">AUM Comparison</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={aumData}>
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={fmtAUM} />
                  <Tooltip formatter={(v) => fmtAUM(v)} />
                  <Bar dataKey="AUM" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-500 border-b border-border">
                <tr>
                  <th className="pb-2 pr-4">Metric</th>
                  {entries.map((d) => (
                    <th key={d.firm.crd_number} className="pb-2 pr-4">
                      <Link to={`/firm/${d.firm.crd_number}`} className="text-accent hover:underline">
                        {d.firm.legal_name?.slice(0, 20) || d.firm.crd_number}
                      </Link>
                      <button
                        onClick={() => removeFirm(d.firm.crd_number)}
                        className="ml-2 text-gray-500 hover:text-red-400"
                        title="Remove"
                      >
                        &times;
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <CompRow label="AUM" values={entries.map((d) => fmtAUM(d.firm.aum_total))} />
                <CompRow label="Employees" values={entries.map((d) => fmtNum(d.firm.employee_count))} />
                <CompRow label="Clients" values={entries.map((d) => fmtNum(d.firm.client_count))} />
                <CompRow label="DRP Count" values={entries.map((d) => String(d.firm.drp_count || 0))} />
                <CompRow label="Risk Flags" values={entries.map((d) => String(d.flags?.length || 0))} />
                <CompRow label="Strategy" values={entries.map((d) => d.firm.primary_strategy || "-")} />
                <CompRow label="Location" values={entries.map((d) => [d.firm.city, d.firm.state].filter(Boolean).join(", ") || "-")} />
                <CompRow label="Disclosures" values={entries.map((d) => String(d.disclosures?.length || 0))} />
                <CompRow label="Registration" values={entries.map((d) => d.firm.registration_date || "-")} />
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function CompRow({ label, values }) {
  return (
    <tr>
      <td className="py-2 pr-4 text-gray-500 font-medium">{label}</td>
      {values.map((v, i) => (
        <td key={i} className="py-2 pr-4 text-gray-300">{v}</td>
      ))}
    </tr>
  );
}
