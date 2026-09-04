import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, CheckCircle2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner, Metric } from "@/components/common";
import { dateIST, timeIST } from "@/lib/format";

export default function Evals() {
  const qc = useQueryClient();
  const latest = useQuery({ queryKey: ["evals-latest"], queryFn: api.evalsLatest });
  const run = useMutation({
    mutationFn: () => api.evalsRun(6),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evals-latest"] }),
  });

  const lr = latest.data?.latest_run;
  const results = latest.data?.results || [];
  const passRate = lr ? Math.round((lr.passed / lr.total) * 100) : 0;

  return (
    <div className="space-y-4" data-testid="evals-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-100">EVALS Engine</h1>
          <p className="text-sm text-slate-500">AI grounding + synthetic hallucination detection · deterministic values are authoritative</p>
        </div>
        <button data-testid="run-evals-btn" onClick={() => run.mutate()} disabled={run.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-cyan text-[#08111f] font-semibold text-sm rounded hover:bg-cyan/90 disabled:opacity-50">
          <Play size={14} /> {run.isPending ? "Running…" : "Run Evaluation Suite"}
        </button>
      </div>

      {latest.isLoading ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-surface-2 rounded overflow-hidden border border-surface-2">
            <Metric label="Pass Rate" value={`${passRate}%`} valueClass={passRate >= 90 ? "text-bull" : passRate >= 60 ? "text-watch" : "text-bear"} />
            <Metric label="Passed" value={lr?.passed ?? "—"} valueClass="text-bull" />
            <Metric label="Failed" value={lr?.failed ?? "—"} valueClass="text-bear" />
            <Metric label="Total Cases" value={lr?.total ?? "—"} />
            <Metric label="Avg Score" value={lr?.avg_score != null ? lr.avg_score.toFixed(2) : "—"} sub={lr ? `run ${timeIST(lr.started_at)}` : ""} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Panel>
              <PanelHeader title="Evaluation Datasets" />
              <div className="divide-y divide-surface-2/60">
                {latest.data?.datasets?.map((ds) => (
                  <div key={ds.id} className="px-4 py-2.5" data-testid={`dataset-${ds.id}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-200 font-medium">{ds.name}</span>
                      <span className="text-[10px] font-mono text-slate-500 border border-surface-2 rounded px-1.5">{ds.version}</span>
                    </div>
                    <div className="text-xs text-slate-500">{ds.description}</div>
                    <div className="text-[10px] font-mono text-slate-600 mt-0.5">kind: {ds.kind}</div>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel className="lg:col-span-2">
              <PanelHeader title="Latest Run — Case Results" right={lr && <span className="text-[10px] font-mono text-slate-500">run_id {lr.id?.slice(0, 8)}</span>} />
              {results.length === 0 ? (
                <div className="p-6 text-center text-slate-500 text-sm">No run yet — click “Run Evaluation Suite”.</div>
              ) : (
                <div className="divide-y divide-surface-2/60 max-h-[420px] overflow-y-auto">
                  {results.map((r) => (
                    <div key={r.case_id} className="flex items-center gap-3 px-4 py-2.5" data-testid={`eval-result-${r.case_id}`}>
                      {r.passed ? <CheckCircle2 size={15} className="text-bull shrink-0" /> : <XCircle size={15} className="text-bear shrink-0" />}
                      <span className="font-mono text-xs text-slate-200 w-52 truncate">{r.case_id}</span>
                      <span className="text-[10px] font-mono uppercase text-slate-500 border border-surface-2 rounded px-1.5 py-0.5">{r.evaluation_type}</span>
                      <span className="text-xs text-slate-500 flex-1 truncate">{r.detail?.label}</span>
                      <span className="font-mono text-xs text-slate-400">{r.score?.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <Panel>
            <PanelHeader title="Registered Cases" />
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-[10px] uppercase text-slate-500 border-b border-surface-2">
                  {["Case ID", "Dataset", "Type", "Label"].map((h) => <th key={h} className="px-4 py-2 text-left">{h}</th>)}
                </tr></thead>
                <tbody className="font-mono">
                  {latest.data?.cases?.map((c) => (
                    <tr key={c.case_id} className="border-b border-surface-2/60">
                      <td className="px-4 py-2 text-slate-200">{c.case_id}</td>
                      <td className="px-4 py-2 text-slate-500">{c.dataset_id}</td>
                      <td className="px-4 py-2 text-slate-400">{c.evaluation_type}</td>
                      <td className="px-4 py-2 text-slate-400 font-sans text-xs">{c.label}</td>
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
