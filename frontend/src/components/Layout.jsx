import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard, Briefcase, LineChart, Search, TrendingUp, Zap, Clock,
  CheckCircle2, Activity, Settings, Terminal, BookOpen, History, Menu, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { signClass, timeIST } from "@/lib/format";
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
  { label: "Research", icon: BookOpen, path: "/research", testid: "nav-research" },
  { label: "Backtesting", icon: History, path: "/backtesting", testid: "nav-backtesting" },
  { label: "Data Health", icon: Activity, path: "/data-health", testid: "nav-data-health" },
  { label: "Settings", icon: Settings, path: "/settings", testid: "nav-settings" },
];

const Brand = ({ extra }) => (
  <div className="h-12 flex items-center gap-2 px-4 border-b border-surface-2 shrink-0">
    <Terminal size={18} className="text-cyan" />
    <span className="font-display font-bold text-slate-100 tracking-tight">StockAI</span>
    <span className="text-[9px] font-mono text-slate-600 border border-surface-2 rounded px-1 ml-auto">V3</span>
    {extra}
  </div>
);

const NavItems = ({ suffix = "", onNavigate }) => (
  <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
    {NAV.map((n) => (
      <NavLink
        key={n.path}
        to={n.path}
        data-testid={`${n.testid}${suffix}`}
        end={n.path === "/"}
        onClick={onNavigate}
        className={({ isActive }) =>
          `flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors ${
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
);

const NavFooter = () => (
  <div className="p-3 border-t border-surface-2 text-[10px] text-slate-600 font-mono leading-relaxed">
    Research & decision-support only.<br />Not investment advice. No orders placed.
  </div>
);

const IndexTicker = ({ label, view }) => (
  <div className="flex items-center gap-2">
    <span className="text-[11px] text-slate-500 font-mono">{label}</span>
    <span className="text-xs font-mono font-semibold text-slate-200 uppercase">{view?.direction || "—"}</span>
    <span className={`text-xs font-mono ${signClass(view?.direction === "bullish" ? 1 : view?.direction === "bearish" ? -1 : 0)}`}>
      {view?.trend || ""}
    </span>
  </div>
);

const TopBar = ({ onMenu }) => {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const { data } = useQuery({ queryKey: ["overview"], queryFn: api.marketOverview, refetchInterval: 60000 });
  const status = data?.market_status;
  const statusColor = status === "OPEN" ? "text-bull" : status === "PRE-MARKET" ? "text-watch" : "text-slate-400";

  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/stock-analysis?symbol=${q.trim().toUpperCase()}`);
  };

  return (
    <header className="h-12 border-b border-surface-2 bg-[#0B1120] flex items-center px-3 sm:px-4 gap-3 shrink-0">
      <button
        type="button"
        onClick={onMenu}
        data-testid="nav-menu-toggle"
        aria-label="Open navigation menu"
        className="lg:hidden p-2 -ml-1 rounded text-slate-300 hover:bg-surface-2/60 min-w-[44px] min-h-[44px] flex items-center justify-center"
      >
        <Menu size={18} />
      </button>
      <div className="lg:hidden flex items-center gap-1.5 shrink-0">
        <Terminal size={15} className="text-cyan" />
        <span className="font-display font-bold text-sm text-slate-100">StockAI</span>
      </div>
      <div className="hidden md:flex items-center gap-4">
        <IndexTicker label="NIFTY 50" view={data?.context?.nifty} />
        <div className="w-px h-4 bg-surface-2" />
        <IndexTicker label="BANK NIFTY" view={data?.context?.banknifty} />
      </div>
      <div className="flex-1" />
      <span data-testid="market-status-badge" className={`hidden sm:inline text-[11px] font-mono font-bold uppercase ${statusColor}`}>
        ● Market {status || "—"}
      </span>
      <form onSubmit={submit} className="relative w-28 sm:w-56 md:w-64 shrink">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          data-testid="global-symbol-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search symbol…"
          className="w-full bg-surface pl-8 pr-3 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none text-slate-200 placeholder:text-slate-600"
        />
      </form>
      <div className="hidden sm:block"><MockBadge /></div>
      <span className="hidden lg:inline text-[11px] font-mono text-slate-500">{timeIST(data?.as_of)}</span>
    </header>
  );
};

export const Layout = ({ children }) => {
  const [menu, setMenu] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden text-slate-200">
      <aside className="hidden lg:flex w-60 shrink-0 bg-[#0B1120] border-r border-surface-2 flex-col">
        <Brand />
        <NavItems />
        <NavFooter />
      </aside>

      {menu && (
        <div className="fixed inset-0 z-50 lg:hidden" data-testid="mobile-nav-drawer">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMenu(false)} data-testid="mobile-nav-overlay" />
          <aside className="absolute left-0 top-0 bottom-0 w-64 max-w-[85vw] bg-[#0B1120] border-r border-surface-2 flex flex-col animate-fade-up">
            <Brand
              extra={
                <button
                  type="button"
                  onClick={() => setMenu(false)}
                  data-testid="mobile-nav-close"
                  aria-label="Close navigation menu"
                  className="lg:hidden p-2 rounded text-slate-400 hover:text-slate-100 hover:bg-surface-2/60 min-w-[44px] min-h-[44px] flex items-center justify-center"
                >
                  <X size={16} />
                </button>
              }
            />
            <NavItems suffix="-m" onNavigate={() => setMenu(false)} />
            <NavFooter />
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onMenu={() => setMenu(true)} />
        <main className="flex-1 overflow-y-auto terminal-grid-bg">
          <div className="p-3 sm:p-5 max-w-[1600px] mx-auto animate-fade-up">{children}</div>
        </main>
      </div>
    </div>
  );
};
