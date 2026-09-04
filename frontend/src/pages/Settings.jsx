import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Save, Lock } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner } from "@/components/common";

const Field = ({ label, value, onChange, step = "1", suffix }) => (
  <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-2/60">
    <label className="text-xs text-slate-400">{label}</label>
    <div className="flex items-center gap-1">
      <input type="number" step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-28 bg-surface px-2 py-1 text-right font-mono text-sm text-slate-100 rounded border border-surface-2 focus:border-cyan focus:outline-none" />
      {suffix && <span className="text-[10px] text-slate-500 w-6">{suffix}</span>}
    </div>
  </div>
);

const Section = ({ title, section, values, fields, onSave, saving }) => {
  const [local, setLocal] = useState(values);
  useEffect(() => setLocal(values), [values]);
  return (
    <Panel testid={`settings-${section}`}>
      <PanelHeader title={title} right={
        <button data-testid={`save-${section}`} onClick={() => onSave(section, local)} disabled={saving}
          className="flex items-center gap-1.5 text-[11px] font-mono text-cyan hover:text-cyan/80 disabled:opacity-50">
          <Save size={12} /> Save
        </button>} />
      {fields.map((f) => (
        <Field key={f.key} label={f.label} step={f.step} suffix={f.suffix}
          value={local?.[f.key] ?? ""} onChange={(v) => setLocal((s) => ({ ...s, [f.key]: v }))} />
      ))}
    </Panel>
  );
};

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const save = useMutation({
    mutationFn: ({ section, values }) => api.updateSettings(section, values),
    onSuccess: (_, v) => { toast.success(`${v.section} settings saved`); qc.invalidateQueries({ queryKey: ["settings"] }); qc.invalidateQueries({ queryKey: ["scan"] }); },
    onError: (e) => toast.error(e?.response?.data?.detail || "Save failed"),
  });
  const onSave = (section, values) => save.mutate({ section, values });
  const s = data?.settings;

  return (
    <div className="space-y-4" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-display font-bold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-500">Safe, non-sensitive configuration · secrets are never exposed here</p>
      </div>

      {isLoading ? <Spinner /> : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Section title="Risk Engine" section="risk" values={s.risk} onSave={onSave} saving={save.isPending}
            fields={[
              { key: "account_capital", label: "Account Capital (₹)", step: "10000" },
              { key: "risk_per_trade_pct", label: "Risk per Trade", step: "0.1", suffix: "%" },
              { key: "atr_stop_multiplier_swing", label: "Swing Stop × ATR", step: "0.1" },
              { key: "atr_target1_multiplier_swing", label: "Swing Target1 × ATR", step: "0.1" },
              { key: "atr_target2_multiplier_swing", label: "Swing Target2 × ATR", step: "0.1" },
              { key: "atr_stop_multiplier_intraday", label: "Intraday Stop × ATR", step: "0.1" },
            ]} />

          <Section title="Thresholds" section="thresholds" values={s.thresholds} onSave={onSave} saving={save.isPending}
            fields={[
              { key: "shortlist_min_score", label: "AI Shortlist Min Score", step: "1" },
              { key: "shortlist_top_n", label: "AI Finalists (Top N)", step: "1" },
              { key: "stale_market_minutes", label: "Stale Market (min)", step: "1" },
              { key: "stale_fundamental_days", label: "Stale Fundamental (days)", step: "1" },
            ]} />

          <Section title="Cache TTLs (seconds)" section="cache" values={s.cache} onSave={onSave} saving={save.isPending}
            fields={[
              { key: "analysis_ttl_seconds", label: "Analysis TTL", step: "60" },
              { key: "scanner_ttl_seconds", label: "Scanner TTL", step: "60" },
              { key: "ai_ttl_seconds", label: "AI TTL", step: "3600" },
              { key: "market_data_ttl_seconds", label: "Market Data TTL", step: "60" },
            ]} />

          <Panel testid="settings-providers">
            <PanelHeader title="Providers & Secrets" />
            <div className="divide-y divide-surface-2/60">
              {[
                ["Market Data", s.providers?.data, "mock"],
                ["Fundamental", s.providers?.fundamental, "mock"],
                ["News", s.providers?.news, "mock"],
                ["AI Provider", s.providers?.ai, s.providers?.ai_model],
              ].map(([l, v, extra]) => (
                <div key={l} className="flex items-center justify-between px-4 py-2.5">
                  <span className="text-xs text-slate-400">{l}</span>
                  <span className="font-mono text-xs text-watch">{v} {extra && `· ${extra}`}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 px-4 py-3 text-[11px] text-slate-500">
                <Lock size={12} /> API keys (Zerodha, OpenAI, TrueData) are stored server-side only and never surfaced to the UI.
              </div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
