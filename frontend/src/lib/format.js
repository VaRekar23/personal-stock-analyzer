export const fmt = (n, d = 2) =>
  n === null || n === undefined || Number.isNaN(n)
    ? "—"
    : Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });

export const inr = (n, d = 2) => (n === null || n === undefined ? "—" : `₹${fmt(n, d)}`);

export const cr = (n) =>
  n === null || n === undefined ? "—" : `₹${fmt(n / 1, 0)} cr`;

export const pct = (n, d = 2) =>
  n === null || n === undefined ? "—" : `${n >= 0 ? "+" : ""}${fmt(n, d)}%`;

export const signClass = (n) =>
  n === null || n === undefined ? "num-flat" : n > 0 ? "num-pos" : n < 0 ? "num-neg" : "num-flat";

export const biasColor = (bias) => {
  const b = (bias || "").toLowerCase();
  if (b === "long" || b === "bullish") return "#10B981";
  if (b === "short" || b === "bearish") return "#EF4444";
  return "#94A3B8";
};

export const timeIST = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("en-IN", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      timeZone: "Asia/Kolkata",
    }) + " IST";
  } catch { return iso; }
};

export const dateIST = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch { return iso; }
};

export const isStale = (iso, minutes = 20) => {
  if (!iso) return true;
  return (Date.now() - new Date(iso).getTime()) / 60000 > minutes;
};

export const MODES = [
  { key: "long_term", label: "Long Term" },
  { key: "swing", label: "Swing" },
  { key: "intraday", label: "Intraday" },
];
export const modeLabel = (k) => MODES.find((m) => m.key === k)?.label || k;
