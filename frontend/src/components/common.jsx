import React from "react";
import { useQuery } from "@tanstack/react-query";
import { biasColor } from "@/lib/format";
import { api } from "@/lib/api";

export const Panel = ({ children, className = "", testid, ...rest }) => (
  <div data-testid={testid} className={`panel ${className}`} {...rest}>
    {children}
  </div>
);

export const PanelHeader = ({ title, right, icon: Icon }) => (
  <div className="flex items-center justify-between px-4 py-3 border-b border-surface-2">
    <div className="flex items-center gap-2">
      {Icon && <Icon size={14} className="text-cyan" />}
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
    </div>
    {right}
  </div>
);

// Dynamic data-source badge: reflects whether live providers are actually
// active (from /api/health), not a hardcoded label. Shows the live mock/live
// breakdown for market, fundamentals, news and AI.
export const MockBadge = ({ className = "" }) => {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30000,
    retry: 1,
  });
  const live = data?.live;
  const anyLive = live && (live.market || live.fundamental || live.news || live.ai);
  const marketLive = !!live?.market;

  const label = !data
    ? "Connecting…"
    : marketLive
    ? "Live Market Data"
    : anyLive
    ? "Partial Live Data"
    : "Demo / Mock Data";

  const tone = marketLive
    ? "border-bull/40 bg-bull/10 text-bull"
    : anyLive
    ? "border-cyan/40 bg-cyan/10 text-cyan"
    : "border-watch/40 bg-watch/10 text-watch";
  const dot = marketLive ? "bg-bull" : anyLive ? "bg-cyan" : "bg-watch";

  const liveList = live
    ? ["market", "fundamental", "news", "ai"]
        .map((k) => `${k}:${live[k] ? "live" : "mock"}`)
        .join(" · ")
    : "";

  return (
    <span
      data-testid="mock-data-badge"
      title={liveList || "Provider status unavailable"}
      className={`inline-flex items-center gap-1 text-[10px] font-mono font-semibold uppercase tracking-wide px-2 py-0.5 rounded border ${tone} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot} pulse-dot`} /> {label}
    </span>
  );
};

export const StaleBadge = ({ className = "" }) => (
  <span className={`inline-flex items-center gap-1 text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded border border-bear/40 bg-bear/10 text-bear ${className}`}>
    Stale Data
  </span>
);

const PILL = {
  operational: "border-bull/40 bg-bull/10 text-bull",
  "demo-mock": "border-watch/40 bg-watch/10 text-watch",
  degraded: "border-watch/40 bg-watch/10 text-watch",
  down: "border-bear/40 bg-bear/10 text-bear",
  "pending-v2": "border-slate-600 bg-slate-700/30 text-slate-400",
};
export const StatusPill = ({ status, testid }) => {
  const key = (status || "").toLowerCase();
  return (
    <span
      data-testid={testid}
      className={`inline-flex items-center gap-1.5 text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded border ${PILL[key] || PILL["down"]}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" /> {status}
    </span>
  );
};

export const BiasBadge = ({ bias, testid }) => {
  const color = biasColor(bias);
  return (
    <span
      data-testid={testid}
      className="inline-flex items-center text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded border"
      style={{ color, borderColor: `${color}66`, backgroundColor: `${color}1a` }}
    >
      {bias || "—"}
    </span>
  );
};

export const ScoreBar = ({ score, width = 64 }) => {
  const s = Math.max(0, Math.min(100, score || 0));
  const color = s >= 60 ? "#10B981" : s <= 40 ? "#EF4444" : "#F59E0B";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden" style={{ width }}>
        <div className="h-full rounded-full" style={{ width: `${s}%`, backgroundColor: color }} />
      </div>
      <span className="font-mono text-xs font-semibold" style={{ color }}>{s.toFixed(0)}</span>
    </div>
  );
};

export const ConfidenceGauge = ({ value }) => {
  const v = Math.max(0, Math.min(1, value || 0));
  const deg = v * 180;
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-28 h-14 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full border-[10px] border-surface-2 border-b-0" style={{ width: 112, height: 56 }} />
        <div
          className="absolute bottom-0 left-1/2 w-0.5 h-12 origin-bottom bg-cyan"
          style={{ transform: `translateX(-50%) rotate(${deg - 90}deg)` }}
        />
      </div>
      <div className="font-mono text-lg font-bold text-cyan -mt-1">{(v * 100).toFixed(0)}%</div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">Confidence</div>
    </div>
  );
};

export const FactorBars = ({ factors = [] }) => (
  <div className="space-y-2">
    {factors.map((f) => {
      const c = f.contribution || 0;
      const width = Math.min(50, Math.abs(c));
      const color = c >= 0 ? "#10B981" : "#EF4444";
      return (
        <div key={f.key} className="flex items-center gap-2 text-xs" data-testid={`factor-${f.key}`}>
          <div className="w-40 text-slate-400 truncate">{f.label}</div>
          <div className="flex-1 flex items-center">
            <div className="w-1/2 flex justify-end">
              {c < 0 && <div className="h-3 rounded-l" style={{ width: `${width * 2}%`, backgroundColor: color, opacity: 0.7 }} />}
            </div>
            <div className="w-px h-4 bg-surface-3" />
            <div className="w-1/2">
              {c >= 0 && <div className="h-3 rounded-r" style={{ width: `${width * 2}%`, backgroundColor: color, opacity: 0.7 }} />}
            </div>
          </div>
          <div className="w-12 text-right font-mono font-semibold" style={{ color }}>
            {c >= 0 ? "+" : ""}{c.toFixed(1)}
          </div>
        </div>
      );
    })}
  </div>
);

export const Spinner = ({ label = "Loading…" }) => (
  <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
    <div className="w-4 h-4 rounded-full border-2 border-cyan border-t-transparent animate-spin" />
    <span className="text-sm font-mono">{label}</span>
  </div>
);

export const ErrorState = ({ title = "Couldn't load data", hint, error }) => (
  <div data-testid="error-state" className="text-center py-16">
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-bear/40 bg-bear/10 text-bear text-xs font-mono font-semibold uppercase tracking-wide">
      {title}
    </div>
    {hint && <div className="text-slate-500 text-sm mt-3 max-w-md mx-auto">{hint}</div>}
    {error && (
      <div className="text-slate-600 text-[11px] font-mono mt-2 max-w-lg mx-auto break-words">
        {String(error?.response?.data?.detail || error?.message || error)}
      </div>
    )}
  </div>
);

export const EmptyState = ({ title, hint }) => (
  <div className="text-center py-16">
    <div className="text-slate-300 font-display text-lg">{title}</div>
    {hint && <div className="text-slate-500 text-sm mt-1">{hint}</div>}
  </div>
);

export const Metric = ({ label, value, sub, valueClass = "text-slate-100" }) => (
  <div className="px-4 py-3">
    <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
    <div className={`font-mono text-xl font-bold ${valueClass}`}>{value}</div>
    {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
  </div>
);
