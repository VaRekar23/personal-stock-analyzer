import React from "react";

const Field = ({ label, children }) => (
  <label className="block">
    <span className="text-[10px] uppercase tracking-wider text-slate-500">{label}</span>
    <div className="mt-1">{children}</div>
  </label>
);

const inputCls = "w-full bg-surface px-2 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none";

export const BacktestForm = ({ form, setForm, intervals, onCoverage, onPrepare, onRun, busy }) => {
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const setMode = (e) => {
    const mode = e.target.value;
    setForm({ ...form, mode, interval: (intervals[mode] || ["1d"])[0] });
  };
  return (
    <div className="p-4 space-y-3" data-testid="backtest-form">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Strategy">
          <select value={form.mode} onChange={setMode} className={inputCls} data-testid="bt-mode-select">
            <option value="swing">Swing (swing_v1)</option>
            <option value="intraday">Intraday (intraday_v1)</option>
          </select>
        </Field>
        <Field label="Interval">
          <select value={form.interval} onChange={set("interval")} className={inputCls} data-testid="bt-interval-select">
            {(intervals[form.mode] || []).map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </Field>
      </div>
      <Field label="Symbols (comma-separated, max 10)">
        <input value={form.symbols} onChange={set("symbols")} className={inputCls} data-testid="bt-symbols-input" placeholder="RELIANCE, ITC" />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Start"><input type="date" value={form.start} onChange={set("start")} className={inputCls} data-testid="bt-start-input" /></Field>
        <Field label="End"><input type="date" value={form.end} onChange={set("end")} className={inputCls} data-testid="bt-end-input" /></Field>
        <Field label="Capital (₹, hypothetical)"><input type="number" value={form.capital} onChange={set("capital")} className={inputCls} data-testid="bt-capital-input" /></Field>
        <Field label="Risk per trade %"><input type="number" step="0.1" value={form.risk_per_trade_pct} onChange={set("risk_per_trade_pct")} className={inputCls} data-testid="bt-risk-input" /></Field>
        <Field label="Slippage (bps)"><input type="number" value={form.slippage_bps} onChange={set("slippage_bps")} className={inputCls} data-testid="bt-slippage-input" /></Field>
        <Field label="Costs (bps / side)"><input type="number" value={form.cost_bps_per_side} onChange={set("cost_bps_per_side")} className={inputCls} data-testid="bt-cost-input" /></Field>
      </div>
      <div className="text-[10px] text-slate-500">Index-wide universes are disabled until point-in-time membership is verified.</div>
      <div className="grid grid-cols-3 gap-2">
        <button onClick={onCoverage} disabled={busy} data-testid="bt-coverage-btn"
          className="px-2 py-2 text-xs font-mono rounded border border-surface-2 text-slate-300 hover:border-cyan disabled:opacity-40">Check data</button>
        <button onClick={onPrepare} disabled={busy} data-testid="bt-prepare-btn"
          className="px-2 py-2 text-xs font-mono rounded border border-surface-2 text-slate-300 hover:border-cyan disabled:opacity-40">Prepare data</button>
        <button onClick={onRun} disabled={busy} data-testid="bt-run-btn"
          className="px-2 py-2 text-xs font-mono rounded bg-cyan/15 text-cyan border border-cyan/30 hover:bg-cyan/25 disabled:opacity-40">Run backtest</button>
      </div>
    </div>
  );
};
