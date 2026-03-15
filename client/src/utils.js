export function fmtAUM(value) {
  if (value == null) return "N/A";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function fmtNum(n) {
  if (n == null) return "N/A";
  return n.toLocaleString();
}

export function fmtDate(dateStr) {
  if (!dateStr) return "N/A";
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function fmtPct(value) {
  if (value == null) return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

const SEVERITY_COLORS = {
  CRITICAL: "bg-red-500/20 text-red-400 border-red-500/30",
  HIGH: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  MEDIUM: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  LOW: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

const SEVERITY_DOTS = {
  CRITICAL: "bg-red-500",
  HIGH: "bg-orange-500",
  MEDIUM: "bg-yellow-500",
  LOW: "bg-blue-500",
};

export function severityClass(severity) {
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.LOW;
}

export function severityDot(severity) {
  return SEVERITY_DOTS[severity] || SEVERITY_DOTS.LOW;
}

const MATERIALITY_COLORS = {
  MATERIAL: "text-red-400",
  MODERATE: "text-yellow-400",
  MINOR: "text-blue-400",
};

export function materialityColor(mat) {
  return MATERIALITY_COLORS[mat] || "text-gray-400";
}

export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}
