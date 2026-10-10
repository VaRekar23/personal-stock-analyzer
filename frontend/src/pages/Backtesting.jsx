import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { History } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Panel, PanelHeader } from "@/components/common";
import { BacktestForm } from "@/components/backtest/BacktestForm";
import { CoverageReport } from "@/components/backtest/CoverageReport";
import { RunList } from "@/components/backtest/RunList";
import { RunDetail } from "@/components/backtest/RunDetail";
import { StrategyEvals } from "@/components/backtest/StrategyEvals";

const iso = (d) => d.toISOString().slice(0, 10);
const today = new Date();
const INITIAL = {
  mode: "swing", interval: "1d", symbols: "RELIANCE, ITC",
  start: iso(new Date(today.getTime() - 270 * 864e5)), end: iso(today),
  capital: 1000000, risk_per_trade_pct: 1, slippage_bps: 5, cost_bps_per_side: 10,
};
const errMsg = (e) => e?.response?.data?.detail || e?.message || "Request failed";

export default function Backtesting() {
  const qc = useQueryClient();
  const [form, setForm] = useState(INITIAL);
  const [selected, setSelected] = useState(null);
  const options = useQuery({ queryKey: ["bt-options"], queryFn: api.backtestOptions });
  const runs = useQuery({ queryKey: ["bt-runs"], queryFn: api.backtestList, refetchInterval: 5000 });

  const body = () => ({
    ...form,
    symbols: form.symbols.split(",").map((s) => s.trim()).filter(Boolean),
    capital: Number(form.capital), risk_per_trade_pct: Number(form.risk_per_trade_pct),
    slippage_bps: Number(form.slippage_bps), cost_bps_per_side: Number(form.cost_bps_per_side),
  });
  const coverage = useMutation({ mutationFn: () => api.backtestCoverage(body()), onError: (e) => toast.error(errMsg(e)) });
  const prepare = useMutation({
    mutationFn: () => api.backtestPrepare(body()),
    onSuccess: (r) => { toast.success(`Fetched ${r.prepared.reduce((a, p) => a + p.candles_fetched, 0)} candles`); coverage.mutate(); },
    onError: (e) => toast.error(errMsg(e)),
  });
  const create = useMutation({
    mutationFn: () => api.backtestCreate(body()),
    onSuccess: (r) => {
      setSelected(r.id);
      toast.success(r.reused ? "Identical run found — showing stored result" : "Backtest queued");
      qc.invalidateQueries({ queryKey: ["bt-runs"] });
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-display font-bold text-slate-100 flex items-center gap-2"><History size={22} /> Backtesting</h1>
        <p className="text-sm text-slate-500">Historical replay of deterministic strategies · no look-ahead · stored candles only · not investment advice</p>
      </div>
      {options.data?.data_source === "mock" && (
        <div data-testid="bt-mock-mode-banner" className="text-xs text-watch bg-watch/10 border border-watch/30 rounded p-2">
          Market data is in MOCK mode — stored candles are synthetic. Connect Zerodha in Settings to prepare real history.
        </div>
      )}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="space-y-5">
          <Panel testid="bt-setup-panel">
            <PanelHeader title="Backtest Setup" />
            <BacktestForm form={form} setForm={setForm} intervals={options.data?.mode_intervals || { swing: ["1d"], intraday: ["15m", "5m"] }}
              onCoverage={() => coverage.mutate()} onPrepare={() => prepare.mutate()} onRun={() => create.mutate()}
              busy={coverage.isPending || prepare.isPending || create.isPending} />
            <CoverageReport data={coverage.data} />
          </Panel>
          <Panel testid="bt-runs-panel"><PanelHeader title="Runs" /><RunList runs={runs.data?.runs} selected={selected} onSelect={setSelected} /></Panel>
          <Panel testid="bt-evals-panel"><PanelHeader title="Strategy EVALS" /><StrategyEvals /></Panel>
        </div>
        <Panel testid="bt-results-panel" className="xl:col-span-2">
          <PanelHeader title="Run Results" />
          <RunDetail id={selected} />
        </Panel>
      </div>
    </div>
  );
}
