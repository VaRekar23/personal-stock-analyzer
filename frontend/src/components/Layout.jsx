import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard, Briefcase, LineChart, Search, TrendingUp, Zap, Clock,
  CheckCircle2, Activity, Settings, Terminal,
} from "lucide-react";
import { api } from "@/lib/api";
import { pct, signClass, timeIST } from "@/lib/format";
import { MockBadge } from "@/components/common";

const NAV = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/", testid: "nav-dashboard" },
  { label: "Portfolio", icon: Briefcase, path: "/portfolio", testid: "nav-portfolio" },
  { label: "Stock Analysis", icon: LineChart, path: "/stock-analysis", testid: "nav-stock-analysis" },
  { label: "NIFTY 50 Scanner", icon: Search, path: "/scanner", testid: "nav-scanner" },
  { label: "Long Term", icon: TrendingUp, path: "/mode/long_term", testid: "nav-long-term" },
  { label: "Swing", icon: Zap, path: "/mode/swing", testid: "nav-swing" },
  { label: "Intraday", icon: Clock, path: "/mode/intraday", testid: "nav-intraday" },
  { label: "EVALS", icon: CheckCircle2, path: "/evals", testid: "nav-evals" },
  { label: "Data Health", icon: Activity, path: "/data-health", testid: "nav-data-health" },
  { label: "Settings", icon: Settings, path: "/settings", testid: "nav-settings" },
];

const IndexTicker = ({ label, view }) => (
  <div className="flex items-center gap-2">
    <span className="text-[11px] text-slate-500 font-mono">{label}</span>
    <span className="text-xs font-mono font-semibold text-slate-200 uppercase">{view?.direction || "—"}</span>
    <span className={`text-xs font-mono ${view?.direction === "bullish" ? "num-pos" : view?.direction === "bearish" ? "num-neg" : "num-flat"}`}>
      {view?.trend || ""}
    </span>
  </div>
);

const TopBar = () => {
  const navigate = useNavigate();
  const [q, setQ] = React.useState("");
  const { data } = useQuery({ queryKey: ["overview"], queryFn: api.marketOverview, refetchInterval: 60000 });
  const status = data?.market_status;
  const statusColor = status === "OPEN" ? "text-bull" : status === "PRE-MARKET" ? "text-watch" : "text-slate-400";

  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/stock-analysis?symbol=${q.trim().toUpperCase()}`);
  };

  return (
    <header className="h-12 border-b border-surface-2 bg-[#0B1120] flex items-center px-4 gap-4 shrink-0">
      <div className="flex items-center gap-4">
        <IndexTicker label="NIFTY 50" view={data?.context?.nifty} />
        <div className="w-px h-4 bg-surface-2" />
        <IndexTicker label="BANK NIFTY" view={data?.context?.banknifty} />
      </div>
      <div className="flex-1" />
      <span data-testid="market-status-badge" className={`text-[11px] font-mono font-bold uppercase ${statusColor}`}>
        ● Market {status || "—"}
      </span>
      <form onSubmit={submit} className="relative">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          data-testid="global-symbol-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search symbol… (e.g. RELIANCE)"
          className="w-64 bg-surface pl-8 pr-3 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none text-slate-200 placeholder:text-slate-600"
        />
      </form>
      <MockBadge />
      <span className="text-[11px] font-mono text-slate-500">{timeIST(data?.as_of)}</span>
    </header>
  );
};

export const Layout = ({ children }) => (
  <div className="flex h-screen overflow-hidden text-slate-200">
    <aside className="w-60 shrink-0 bg-[#0B1120] border-r border-surface-2 flex flex-col">
      <div className="h-12 flex items-center gap-2 px-4 border-b border-surface-2">
        <Terminal size={18} className="text-cyan" />
        <span className="font-display font-bold text-slate-100 tracking-tight">StockAI</span>
        <span className="text-[9px] font-mono text-slate-600 border border-surface-2 rounded px-1 ml-auto">V1</span>
      </div>
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {NAV.map((n) => (
          <NavLink
            key={n.path}
            to={n.path}
            data-testid={n.testid}
            end={n.path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                isActive
                  ? "bg-cyan/10 text-cyan border-l-2 border-cyan"
                  : "text-slate-400 hover:text-slate-100 hover:bg-surface-2/50 border-l-2 border-transparent"
              }`
            }
          >
            <n.icon size={16} />
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-surface-2 text-[10px] text-slate-600 font-mono leading-relaxed">
        Research & decision-support only.<br />Not investment advice. No orders placed.
      </div>
    </aside>
    <div className="flex-1 flex flex-col min-w-0">
      <TopBar />
      <main className="flex-1 overflow-y-auto terminal-grid-bg">
        <div className="p-5 max-w-[1600px] mx-auto animate-fade-up">{children}</div>
      </main>
    </div>
  </div>
);
