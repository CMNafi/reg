import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { searchFirms } from "../api";
import { fmtAUM, fmtNum, severityDot, cn } from "../utils";

export default function Home() {
  const navigate = useNavigate();
  const [firms, setFirms] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [state, setState] = useState("");
  const [minAum, setMinAum] = useState("");
  const [maxAum, setMaxAum] = useState("");
  const [selected, setSelected] = useState(new Set());
  const debounceRef = useRef(null);

  function doSearch(q, st, min, max) {
    setLoading(true);
    searchFirms({
      q: q || undefined,
      state: st || undefined,
      min_aum: min || undefined,
      max_aum: max || undefined,
    })
      .then((data) => {
        setFirms(data.firms || []);
        setTotal(data.total || 0);
      })
      .catch(() => setFirms([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    doSearch("", "", "", "");
  }, []);

  function handleQueryChange(val) {
    setQuery(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val, state, minAum, maxAum), 300);
  }

  function handleFilterChange(st, min, max) {
    setState(st);
    setMinAum(min);
    setMaxAum(max);
    doSearch(query, st, min, max);
  }

  function toggleSelect(crd) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(crd)) next.delete(crd);
      else if (next.size < 5) next.add(crd);
      return next;
    });
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-1">RegIntel</h1>
        <p className="text-gray-400">
          SEC investment adviser intelligence — real-time risk monitoring and regulatory data
        </p>
      </header>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          placeholder="Search firms by name or CRD..."
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          className="flex-1 bg-panel border border-border rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent"
        />
        <select
          value={state}
          onChange={(e) => handleFilterChange(e.target.value, minAum, maxAum)}
          className="bg-panel border border-border rounded-lg px-3 py-2.5 text-sm text-gray-300"
        >
          <option value="">All States</option>
          {["CT", "IL", "NY", "CA", "TX", "FL", "MA"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Min AUM"
          value={minAum}
          onChange={(e) => handleFilterChange(state, e.target.value, maxAum)}
          className="w-32 bg-panel border border-border rounded-lg px-3 py-2.5 text-sm text-gray-300 placeholder-gray-500"
        />
        <input
          type="number"
          placeholder="Max AUM"
          value={maxAum}
          onChange={(e) => handleFilterChange(state, minAum, e.target.value)}
          className="w-32 bg-panel border border-border rounded-lg px-3 py-2.5 text-sm text-gray-300 placeholder-gray-500"
        />
      </div>

      {selected.size > 1 && (
        <div className="mb-4">
          <button
            onClick={() => navigate(`/compare?firms=${[...selected].join(",")}`)}
            className="bg-accent hover:bg-accent-hover text-white text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            Compare {selected.size} Firms
          </button>
        </div>
      )}

      <p className="text-xs text-gray-500 mb-3">{total} firms found</p>

      {loading ? (
        <div className="text-center py-20 text-gray-500">Loading...</div>
      ) : firms.length === 0 ? (
        <div className="text-center py-20 text-gray-500">No firms found</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {firms.map((firm) => (
            <FirmCard
              key={firm.crd_number}
              firm={firm}
              isSelected={selected.has(firm.crd_number)}
              onSelect={() => toggleSelect(firm.crd_number)}
              onClick={() => navigate(`/firm/${firm.crd_number}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FirmCard({ firm, isSelected, onSelect, onClick }) {
  return (
    <div
      className={cn(
        "bg-panel border rounded-lg p-4 cursor-pointer hover:border-accent/50 transition animate-fade-in",
        isSelected ? "border-accent" : "border-border"
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0" onClick={onClick}>
          <h3 className="text-sm font-semibold text-white truncate">
            {firm.legal_name || firm.doing_business_as}
          </h3>
          <p className="text-xs text-gray-500">CRD {firm.crd_number}</p>
        </div>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          className="ml-2 mt-1 accent-blue-500"
          title="Select for comparison"
        />
      </div>
      <div className="space-y-1 text-xs text-gray-400" onClick={onClick}>
        <div className="flex justify-between">
          <span>AUM</span>
          <span className="text-white font-medium">{fmtAUM(firm.aum_total)}</span>
        </div>
        <div className="flex justify-between">
          <span>Employees</span>
          <span>{fmtNum(firm.employee_count)}</span>
        </div>
        <div className="flex justify-between">
          <span>Location</span>
          <span>{[firm.city, firm.state].filter(Boolean).join(", ") || "N/A"}</span>
        </div>
        {firm.primary_strategy && (
          <div className="flex justify-between">
            <span>Strategy</span>
            <span className="truncate ml-2">{firm.primary_strategy}</span>
          </div>
        )}
        {firm.drp_count > 0 && (
          <div className="flex items-center gap-1 mt-1">
            <span className={`w-1.5 h-1.5 rounded-full ${severityDot("HIGH")}`} />
            <span className="text-orange-400">{firm.drp_count} disclosure(s)</span>
          </div>
        )}
      </div>
    </div>
  );
}
