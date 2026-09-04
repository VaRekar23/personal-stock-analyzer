import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Zap, Briefcase, Gauge, ArrowUpRight } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, PanelHeader, ScoreBar, BiasBadge, Spinner, StaleBadge } from "@/components/common";
import { inr, pct, signClass, timeIST, isStale } from "@/lib/format";

const SectorHeat = ({ sectors = [] }) => (
  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 p-4">
    {sectors.map((s) => {
      const c = s.direction === "bullish" ? "#10B981" : s.direction === "bearish" ? "#EF4444" : "#64748B";
      return (
        <div key={s.sector} data-testid={`sector-${s.sector}`}
          className="rounded border border-surface-2 px-3 py-2" style={{ backgroundColor: `${c}14` }}>
          <div className="text-xs font-semibold text-slate-200">{s.sector}</div>
          <div className="text-[10px] font-mono uppercase" style={{ color: c }}>{s.direction}</div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">{s.constituents_bullish}▲ / {s.constituents_bearish}▼</div>
        </div>
      );
    })}
  </div>
);

const CandidateRow = ({ r }) => (
  <Link to={`/stock-analysis?symbol=${r.symbol}&mode=${r.mode || "swing"}`}
    className="flex items-center gap-3 px-4 py-2 hover:bg-surface-2/40 transition-colors" data-testid={`candidate-${r.symbol}`}>
    <span className="w-6 text-slate-600 font-mono text-xs">{r.rank}</span>
    <span className="w-24 font-mono font-semibold text-slate-100 text-sm">{r.symbol}</span>
    <div className="flex-1"><ScoreBar score={r.score} /></div>
    <BiasBadge bias={r.bias} />
    <ArrowUpRight size={13} className="text-slate-600" />
  </Link>
);

export default function Dashboard() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.marketOverview });
  const portfolio = useQuery({ queryKey: ["portfolio"], queryFn: api.portfolio });
  const swing = useQuery({ queryKey: ["scan", "swing"], queryFn: () => api.scan("swing") });
  const longterm = useQuery({ queryKey: ["scan", "long_term"], queryFn: () => api.scan("long_term") });

  const ctx = overview.data?.context;
  const pf = portfolio.data?.summary;

  const IndexCard = ({ title, view }) => {
    const c = view?.direction === "bullish" ? "#10B981" : view?.direction === "bearish" ? "#EF4444" : "#94A3B8";
    return (
      <Panel className="p-4">
        <div className="text-[10px] uppercase tracking-wider text-slate-500">{title}</div>
        <div className="flex items-end justify-between mt-1">
          <div className="font-mono text-2xl font-bold" style={{ color: c }}>{(view?.direction || "—").toUpperCase()}</div>
          <div className="text-right">
            <div className="text-xs font-mono text-slate-400">Trend {view?.trend || "—"}</div>
            <div className="text-xs font-mono text-slate-400">RSI {view?.rsi ?? "—"}</div>
          </div>
        </div>
      </Panel>
    );
  };

  return (
    <div className="space-y-4" data-testid="dashboard-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold tracking-tight text-slate-100">Market Command Center</h1>
          <p className="text-sm text-slate-500">Deterministic analytics · AI explanation layer · NIFTY 50 universe</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
          {isStale(overview.data?.as_of) && <StaleBadge />}
          Updated {timeIST(overview.data?.as_of)}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <IndexCard title="NIFTY 50" view={ctx?.nifty} />
        <IndexCard title="BANK NIFTY" view={ctx?.banknifty} />
        <Panel className="p-4">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Market Breadth</div>
          <div className="font-mono text-2xl font-bold text-slate-100 mt-1 uppercase">{ctx?.breadth || "—"}</div>
          <div className="text-xs text-slate-500 mt-1">Broad regime from index proxies</div>
        </Panel>
        <Panel className="p-4" testid="dashboard-portfolio-health">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1"><Gauge size={12} /> Portfolio Health</div>
          {pf ? (
            <>
              <div className={`font-mono text-2xl font-bold mt-1 ${signClass(pf.pnl)}`}>{pct(pf.pnl_pct)}</div>
              <div className="text-xs text-slate-500 mt-1 font-mono">
                {pf.healthy}✓ Healthy · {pf.watch} Watch · {pf.review} Review
              </div>
            </>
          ) : <div className="text-slate-600 text-sm mt-2">—</div>}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel className="lg:col-span-2">
          <PanelHeader title="Sector Performance Heatmap" icon={TrendingUp} />
          {overview.isLoading ? <Spinner /> : <SectorHeat sectors={overview.data?.sectors} />}
        </Panel>

        <Panel>
          <PanelHeader title="Top Swing Candidates" icon={Zap}
            right={<Link to="/mode/swing" className="text-[10px] font-mono text-cyan hover:underline">VIEW ALL</Link>} />
          {swing.isLoading ? <Spinner /> : (
            <div className="divide-y divide-surface-2">
              {swing.data?.results?.slice(0, 6).map((r) => <CandidateRow key={r.symbol} r={{ ...r, mode: "swing" }} />)}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel>
          <PanelHeader title="Top Long-Term Candidates" icon={TrendingUp}
            right={<Link to="/mode/long_term" className="text-[10px] font-mono text-cyan hover:underline">VIEW ALL</Link>} />
          {longterm.isLoading ? <Spinner /> : (
            <div className="divide-y divide-surface-2">
              {longterm.data?.results?.slice(0, 6).map((r) => <CandidateRow key={r.symbol} r={{ ...r, mode: "long_term" }} />)}
            </div>
          )}
        </Panel>

        <Panel>
          <PanelHeader title="Holdings Requiring Review" icon={Briefcase}
            right={<Link to="/portfolio" className="text-[10px] font-mono text-cyan hover:underline">PORTFOLIO</Link>} />
          {portfolio.isLoading ? <Spinner /> : (
            <div className="divide-y divide-surface-2">
              {(portfolio.data?.top_risks?.length ? portfolio.data.top_risks : [{ symbol: "—", reason: "No holdings flagged for review", pnl_pct: null }]).map((r, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-2.5" data-testid={`risk-${r.symbol}`}>
                  <span className="w-24 font-mono font-semibold text-slate-100 text-sm">{r.symbol}</span>
                  <span className="flex-1 text-xs text-slate-400">{r.reason}</span>
                  <span className={`font-mono text-xs ${signClass(r.pnl_pct)}`}>{r.pnl_pct === null ? "" : pct(r.pnl_pct)}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
