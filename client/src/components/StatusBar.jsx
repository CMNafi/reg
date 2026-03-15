import { useState, useEffect } from "react";
import { getHealth } from "../api";

export default function StatusBar() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const poll = () => getHealth().then(setHealth).catch(() => setHealth(null));
    poll();
    const id = setInterval(poll, 30000);
    return () => clearInterval(id);
  }, []);

  const online = health?.status === "online";

  return (
    <div className="fixed bottom-0 inset-x-0 bg-panel border-t border-border px-4 py-1.5 flex items-center gap-4 text-xs text-gray-400 z-50">
      <span className="flex items-center gap-1.5">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            online ? "bg-emerald-500 animate-pulse-dot" : "bg-red-500"
          }`}
        />
        {online ? "Connected" : "Disconnected"}
      </span>
      {health && (
        <>
          <span>{health.total_firms} firms</span>
          <span>{health.active_flags} active flags</span>
          {health.critical_flags > 0 && (
            <span className="text-red-400">{health.critical_flags} critical</span>
          )}
          <span>
            AI: {health.claude_api === "configured" ? "Ready" : "Not configured"}
          </span>
        </>
      )}
    </div>
  );
}
