import React from "react";
import { AlertTriangle } from "lucide-react";

export const WarningList = ({ warnings = [], testid = "bt-warnings" }) =>
  warnings.length > 0 && (
    <div data-testid={testid} className="text-[11px] text-watch bg-watch/10 border border-watch/30 rounded p-2 space-y-0.5">
      {warnings.map((w, i) => (
        <div key={i} className="flex items-start gap-1.5"><AlertTriangle size={12} className="shrink-0 mt-0.5" />{w}</div>
      ))}
    </div>
  );

export const CoverageReport = ({ data }) => {
  if (!data) return null;
  return (
    <div className="px-4 pb-4 space-y-2" data-testid="bt-coverage-report">
      <table className="w-full text-[11px] font-mono">
        <thead className="text-slate-500 text-left">
          <tr><th>Symbol</th><th>Bars</th><th>Warm-up</th><th>First</th><th>Last</th><th>Gaps</th><th>Source</th></tr>
        </thead>
        <tbody className="text-slate-300">
          {data.coverage.map((c) => (
            <tr key={c.symbol} data-testid="bt-coverage-row">
              <td>{c.symbol}</td><td>{c.bars}</td><td>{c.warmup_bars ?? "—"}</td>
              <td>{c.first || "—"}</td><td>{c.last || "—"}</td><td>{c.gap_count ?? "—"}</td>
              <td className={c.synthetic ? "text-bear" : "text-bull"}>{(c.sources || []).join(",") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <WarningList warnings={data.warnings} testid="bt-coverage-warnings" />
    </div>
  );
};
