import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Briefcase } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner, Metric, MockBadge } from "@/components/common";
import { inr, pct, signClass, fmt, timeIST } from "@/lib/format";

const HEALTH = {
  Healthy: "bg-bull/10 text-bull border-bull/30",
  Watch: "bg-watch/10 text-watch border-watch/30",
  Review: "bg-bear/10 text-bear border-bear/30",
};

export default function Portfolio() {
  const { data, isLoading } = useQuery({ queryKey: ["portfolio"], queryFn: api.portfolio });
  const s = data?.summary;

  return (
    <div className="space-y-4" data-testid="portfolio-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-100">Portfolio Intelligence</h1>
          <p className="text-sm text-slate-500">Zerodha holdings (mock) · deterministic health rules · no orders placed</p>
        </div>
        <MockBadge />
      </div>

      {isLoading ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-px bg-surface-2 rounded overflow-hidden border border-surface-2">
            <Metric label="Holdings" value={s.holdings_count} />
            <Metric label="Invested" value={inr(s.invested, 0)} />
            <Metric label="Current Value" value={inr(s.current_value, 0)} />
            <Metric label="Net P&L" value={inr(s.pnl, 0)} valueClass={signClass(s.pnl)} sub={pct(s.pnl_pct)} />
            <Metric label="Healthy" value={s.healthy} valueClass="text-bull" />
            <Metric label="Watch" value={s.watch} valueClass="text-watch" />
            <Metric label="Review" value={s.review} valueClass="text-bear" />
          </div>

          <Panel>
            <PanelHeader title="Holdings" icon={Briefcase}
              right={<span className="text-[11px] font-mono text-slate-500">as of {timeIST(data.as_of)}</span>} />
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="holdings-table">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-surface-2">
                    {["Symbol", "Sector", "Qty", "Avg", "LTP", "Invested", "Current", "P&L", "P&L %", "Bias", "Health"].map((h) => (
                      <th key={h} className={`px-3 py-2 ${["Symbol", "Sector"].includes(h) ? "text-left" : "text-right"}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {data.holdings.map((h) => (
                    <tr key={h.symbol} className="border-b border-surface-2/60 hover:bg-surface-2/30" data-testid={`holding-${h.symbol}`}>
                      <td className="px-3 py-2 text-left">
                        <Link to={`/stock-analysis?symbol=${h.symbol}&mode=swing`} className="text-slate-100 font-semibold hover:text-cyan">{h.symbol}</Link>
                      </td>
                      <td className="px-3 py-2 text-left text-slate-400 font-sans text-xs">{h.sector}</td>
                      <td className="px-3 py-2 text-right text-slate-300">{h.quantity}</td>
                      <td className="px-3 py-2 text-right text-slate-300">{inr(h.average_price)}</td>
                      <td className="px-3 py-2 text-right text-slate-100">{inr(h.last_price)}</td>
                      <td className="px-3 py-2 text-right text-slate-400">{inr(h.invested, 0)}</td>
                      <td className="px-3 py-2 text-right text-slate-200">{inr(h.current_value, 0)}</td>
                      <td className={`px-3 py-2 text-right ${signClass(h.pnl)}`}>{inr(h.pnl, 0)}</td>
                      <td className={`px-3 py-2 text-right ${signClass(h.pnl_pct)}`}>{pct(h.pnl_pct)}</td>
                      <td className="px-3 py-2 text-right text-xs uppercase" style={{ color: h.swing_bias === "bullish" ? "#10B981" : h.swing_bias === "bearish" ? "#EF4444" : "#94A3B8" }}>{h.swing_bias}</td>
                      <td className="px-3 py-2 text-right">
                        <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${HEALTH[h.health]}`}
                          data-testid={`health-${h.symbol}`} title={h.health_reasons?.join("; ")}>{h.health}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
