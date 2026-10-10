import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Spinner, ErrorState, StatusPill } from "@/components/common";
import { MetricsGrid, EquityCurve, TradesTable } from "./RunResults";
import { WarningList } from "./CoverageReport";

const KV = ({ obj }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 text-[10px] font-mono">
    {Object.entries(obj || {}).map(([k, v]) => (
      <div key={k} className="flex justify-between gap-2 border-b border-surface-2 py-0.5">
        <span className="text-slate-500">{k}</span><span className="text-slate-300 text-right">{String(v)}</span>
      </div>
    ))}
  </div>
);

export const RunDetail = ({ id }) => {
  const q = useQuery({
    queryKey: ["bt-run", id], queryFn: () => api.backtestGet(id), enabled: !!id,
    refetchInterval: (query) => (["queued", "running"].includes(query.state.data?.status) ? 2000 : false),
  });
  if (!id) return <div className="text-xs text-slate-500 p-6 text-center">Select or run a backtest.</div>;
  if (q.isLoading) return <Spinner />;
  if (q.isError) return <ErrorState title="Run unavailable" error={q.error} />;
  const r = q.data;
  return (
    <div className="p-4 space-y-4" data-testid="bt-run-detail">
      <div className="flex items-center justify-between">
        <div className="text-xs font-mono text-slate-300">
          {r.mode} · {r.interval} · {r.symbols.join(", ")} · {r.start_date} → {r.end_date}
        </div>
        <StatusPill status={r.status} testid="bt-run-status" />
      </div>
      {r.synthetic_data && (
        <div data-testid="bt-synthetic-banner" className="text-xs font-bold text-bear bg-bear/10 border border-bear/40 rounded p-2">
          SYNTHETIC / MOCK DATA — this is a development test, NOT a real historical backtest.
        </div>
      )}
      {["queued", "running"].includes(r.status) && <Spinner label="Backtest running…" />}
      {r.status === "failed" && <div className="text-xs text-bear" data-testid="bt-run-error">{r.error}</div>}
      {r.metrics && <MetricsGrid m={r.metrics} />}
      <WarningList warnings={r.warnings || []} />
      {r.equity_curve && <EquityCurve curve={r.equity_curve} />}
      {r.trades?.length > 0 && <TradesTable trades={r.trades} />}
      {r.metrics?.skipped_by_reason && Object.keys(r.metrics.skipped_by_reason).length > 0 && (
        <div data-testid="bt-skipped"><div className="text-xs font-semibold text-slate-300 mb-1">Skipped signals</div><KV obj={r.metrics.skipped_by_reason} /></div>
      )}
      {r.open_trades?.length > 0 && (
        <div className="text-[11px] text-slate-400" data-testid="bt-open-trades">
          Unresolved at end of window (excluded from metrics): {r.open_trades.map((t) => `${t.symbol} ${t.direction} @${t.entry_price}`).join(" · ")}
        </div>
      )}
      <details className="text-xs" data-testid="bt-provenance">
        <summary className="cursor-pointer text-slate-400">Versions, assumptions & data versions</summary>
        <div className="mt-2 space-y-2"><KV obj={r.versions} /><KV obj={r.assumptions} /><KV obj={r.data_versions} /></div>
      </details>
    </div>
  );
};
