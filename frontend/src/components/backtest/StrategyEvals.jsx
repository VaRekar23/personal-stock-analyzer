import React from "react";
import { useMutation } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { api } from "@/lib/api";

export const StrategyEvals = () => {
  const run = useMutation({ mutationFn: api.strategyEvals });
  const d = run.data;
  return (
    <div className="p-4 space-y-2" data-testid="strategy-evals">
      <div className="flex items-center justify-between">
        <div className="text-[10px] text-slate-500">Deterministic accounting checks on SYNTHETIC fixtures (separate from AI EVALS).</div>
        <button onClick={() => run.mutate()} disabled={run.isPending} data-testid="strategy-evals-run-btn"
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-mono rounded border border-surface-2 text-slate-300 hover:border-cyan disabled:opacity-40">
          <FlaskConical size={12} /> {run.isPending ? "Running…" : "Run"}
        </button>
      </div>
      {d && (
        <>
          <div data-testid="strategy-evals-summary" className={`text-sm font-mono ${d.failed ? "text-bear" : "text-bull"}`}>{d.passed}/{d.total} passed</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 text-[10px] font-mono">
            {d.results.map((r) => (
              <div key={r.case_id} className="flex justify-between border-b border-surface-2 py-0.5">
                <span className="text-slate-400">{r.case_id}</span>
                <span className={r.passed ? "text-bull" : "text-bear"}>{r.passed ? "PASS" : "FAIL"}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
