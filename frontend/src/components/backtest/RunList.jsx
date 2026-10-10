import React from "react";
import { StatusPill } from "@/components/common";

const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

export const RunList = ({ runs = [], selected, onSelect }) => (
  <div className="divide-y divide-surface-2 max-h-[360px] overflow-y-auto" data-testid="bt-run-list">
    {runs.length === 0 && <div className="text-xs text-slate-500 p-4 text-center">No runs yet.</div>}
    {runs.map((r) => (
      <button key={r.id} onClick={() => onSelect(r.id)} data-testid="bt-run-row"
        className={`w-full text-left px-4 py-2 hover:bg-surface ${selected === r.id ? "bg-surface" : ""}`}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-200">{r.mode} · {r.interval} · {r.symbols.join(",")}</span>
          <StatusPill status={r.status} />
        </div>
        <div className="text-[10px] font-mono text-slate-500">
          {r.start_date} → {r.end_date} · trades {r.summary?.total_trades ?? "—"} · win {pct(r.summary?.win_rate)}
          {r.synthetic_data && <span className="text-bear ml-1">· SYNTHETIC</span>}
        </div>
      </button>
    ))}
  </div>
);
