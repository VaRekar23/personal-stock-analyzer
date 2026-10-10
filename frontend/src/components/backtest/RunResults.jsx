import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Metric } from "@/components/common";

const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
const num = (v, d = 2) => (v == null ? "—" : Number(v).toLocaleString("en-IN", { maximumFractionDigits: d }));
const pnlCls = (v) => (v > 0 ? "text-bull" : v < 0 ? "text-bear" : "text-slate-100");

export const MetricsGrid = ({ m }) => (
  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 border border-surface-2 rounded divide-x divide-y divide-surface-2" data-testid="bt-metrics">
    <Metric label="Trades" value={m.total_trades} sub={`${m.winning_trades}W / ${m.losing_trades}L`} />
    <Metric label="Win rate" value={pct(m.win_rate)} />
    <Metric label="Net P&L ₹" value={num(m.net_pnl, 0)} valueClass={pnlCls(m.net_pnl)} sub={`gross ${num(m.gross_pnl, 0)}`} />
    <Metric label="Expectancy (R)" value={num(m.expectancy_r, 3)} valueClass={pnlCls(m.expectancy_r)} />
    <Metric label="Profit factor" value={num(m.profit_factor, 2)} sub={m.profit_factor_note || ""} />
    <Metric label="Max drawdown ₹" value={num(m.max_drawdown, 0)} sub={`${num(m.max_drawdown_pct, 2)}%`} />
    <Metric label="Avg return / trade" value={m.avg_return_pct == null ? "—" : `${num(m.avg_return_pct, 2)}%`} />
    <Metric label="Avg hold (bars)" value={num(m.avg_holding_bars, 1)} />
    <Metric label="T1 hit" value={pct(m.target_1_hit_rate)} />
    <Metric label="T2 reached*" value={pct(m.target_2_hit_rate)} sub="counterfactual" />
    <Metric label="Stop hit" value={pct(m.stop_loss_hit_rate)} />
    <Metric label="Open / skipped" value={`${m.open_trades} / ${m.skipped_trades}`} sub={`costs ₹${num(m.total_costs, 0)}`} />
  </div>
);

export const EquityCurve = ({ curve = [] }) =>
  curve.length > 1 && (
    <div className="h-48" data-testid="bt-equity-curve">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={curve.map((p, i) => ({ ...p, i, d: p.ts ? p.ts.slice(0, 10) : "start" }))}>
          <XAxis dataKey="d" tick={{ fontSize: 10, fill: "#64748b" }} minTickGap={40} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#64748b" }} width={70} />
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 11 }} />
          <Line type="stepAfter" dataKey="equity" stroke="#22d3ee" dot={false} strokeWidth={1.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

export const TradesTable = ({ trades = [] }) => (
  <div className="overflow-x-auto max-h-[380px] overflow-y-auto border border-surface-2 rounded">
    <table className="w-full text-[11px] font-mono" data-testid="bt-trades-table">
      <thead className="text-slate-500 text-left sticky top-0 bg-surface">
        <tr>{["Symbol", "Dir", "Entry", "Entry ₹", "Exit", "Exit ₹", "Stop", "T1", "Reason", "Net ₹", "R", "Bars"].map((h) => <th key={h} className="px-2 py-1">{h}</th>)}</tr>
      </thead>
      <tbody className="text-slate-300">
        {trades.map((t, i) => (
          <tr key={i} className="border-t border-surface-2" data-testid="bt-trade-row">
            <td className="px-2 py-1">{t.symbol}</td><td>{t.direction}</td>
            <td>{t.entry_ts.slice(0, 16).replace("T", " ")}</td><td>{num(t.entry_price)}</td>
            <td>{t.exit_ts.slice(0, 16).replace("T", " ")}</td><td>{num(t.exit_price)}</td>
            <td>{num(t.stop_loss)}</td><td>{num(t.target_1)}</td>
            <td>{t.exit_reason}{t.ambiguous ? " ⚠" : ""}</td>
            <td className={pnlCls(t.net_pnl)}>{num(t.net_pnl, 0)}</td>
            <td className={pnlCls(t.r_net)}>{num(t.r_net, 2)}</td><td>{t.bars_held}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
