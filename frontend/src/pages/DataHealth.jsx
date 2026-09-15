import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, Server, Activity, Cpu, Newspaper, BarChart3, BrainCircuit } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner, StatusPill, ErrorState } from "@/components/common";
import { timeIST, dateIST } from "@/lib/format";

const ICONS = {
  database: Database, cache: Server, zerodha: BarChart3,
  fundamental: Activity, news: Newspaper, ai: Cpu, knowledge_rag: BrainCircuit,
};
const LABELS = {
  database: "Database (PostgreSQL)", cache: "Cache (Redis)", zerodha: "Zerodha / Kite",
  fundamental: "Fundamental Data", news: "News Feed", ai: "AI Provider", knowledge_rag: "Knowledge / RAG",
};

export default function DataHealth() {
  const { data, isLoading, isError, error } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15000, retry: 1 });

  return (
    <div className="space-y-4" data-testid="data-health-page">
      <div>
        <h1 className="text-2xl font-display font-bold text-slate-100">Data Health & Observability</h1>
        <p className="text-sm text-slate-500">Provider status · versions · ingestion & analysis freshness</p>
      </div>

      {isLoading ? <Spinner /> : (isError || !data?.services) ? (
        <ErrorState title="Backend unreachable"
          hint="Could not reach the data-health endpoint. Check that the backend service is running and CORS allows this origin."
          error={error} />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(data.services).map(([key, svc]) => {
              const Icon = ICONS[key] || Activity;
              return (
                <Panel key={key} className="p-4 panel-hover" testid={`health-${key}`}>
                  <div className="flex items-center justify-between mb-2">
                    <Icon size={16} className="text-slate-400" />
                    <StatusPill status={svc.status} testid={`status-${key}`} />
                  </div>
                  <div className="text-sm font-medium text-slate-200">{LABELS[key] || key}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{svc.detail}</div>
                  {svc.engine && <div className="text-[10px] font-mono text-slate-600 mt-1">{svc.engine}</div>}
                  {svc.stats && <div className="text-[10px] font-mono text-slate-600 mt-1">hit-rate {(svc.stats.hit_rate * 100).toFixed(0)}% · {svc.stats.backend}</div>}
                </Panel>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel>
              <PanelHeader title="Pipeline Freshness" />
              <div className="divide-y divide-surface-2/60">
                <div className="flex justify-between px-4 py-3"><span className="text-xs text-slate-500">Last Market-Data Ingestion</span>
                  <span className="font-mono text-sm text-slate-200">{data.last_ingestion?.at ? timeIST(data.last_ingestion.at) : "—"}</span></div>
                <div className="flex justify-between px-4 py-3"><span className="text-xs text-slate-500">Ingestion Job</span>
                  <span className="font-mono text-xs text-slate-400">{data.last_ingestion?.job || "—"}</span></div>
                <div className="flex justify-between px-4 py-3"><span className="text-xs text-slate-500">Last Successful Analysis</span>
                  <span className="font-mono text-sm text-slate-200">{data.last_analysis ? `${data.last_analysis.symbol} · ${timeIST(data.last_analysis.at)}` : "—"}</span></div>
                <div className="flex justify-between px-4 py-3"><span className="text-xs text-slate-500">Snapshot</span>
                  <span className="font-mono text-sm text-slate-200">{timeIST(data.as_of)}</span></div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader title="Version Registry" />
              <div className="divide-y divide-surface-2/60 font-mono text-sm">
                <div className="flex justify-between px-4 py-2"><span className="text-slate-500 font-sans text-xs">Indicator</span><span className="text-slate-200">{data.versions.indicator}</span></div>
                <div className="flex justify-between px-4 py-2"><span className="text-slate-500 font-sans text-xs">Scoring</span><span className="text-slate-200">{data.versions.scoring}</span></div>
                <div className="flex justify-between px-4 py-2"><span className="text-slate-500 font-sans text-xs">Risk</span><span className="text-slate-200">{data.versions.risk}</span></div>
                {Object.entries(data.versions.strategies).map(([k, v]) => (
                  <div key={k} className="flex justify-between px-4 py-2"><span className="text-slate-500 font-sans text-xs">Strategy · {k}</span><span className="text-slate-200">{v}</span></div>
                ))}
              </div>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
