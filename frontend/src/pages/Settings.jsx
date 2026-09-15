import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Save, Lock, Link2, ExternalLink, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner, ErrorState } from "@/components/common";

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

const KiteConnect = () => {
  const qc = useQueryClient();
  const [token, setToken] = useState("");
  const { data: st, isLoading } = useQuery({ queryKey: ["kite-status"], queryFn: api.kiteStatus, refetchInterval: 15000 });
  const connect = useMutation({
    mutationFn: (t) => api.kiteConnect(t),
    onSuccess: () => { toast.success("Zerodha Kite connected — live market data enabled"); setToken(""); qc.invalidateQueries(); },
    onError: (e) => toast.error(e?.response?.data?.detail || "Kite connection failed"),
  });
  const logout = useMutation({
    mutationFn: api.kiteLogout,
    onSuccess: () => { toast.success("Disconnected — back to demo data"); qc.invalidateQueries(); },
  });
  const openLogin = async () => {
    try { const r = await api.kiteLoginUrl(); window.open(r.login_url, "_blank", "noopener"); }
    catch (e) { toast.error("Login URL unavailable — check ZERODHA_API_KEY"); }
  };
  const connected = st?.connected;

  return (
    <Panel testid="settings-kite" className="lg:col-span-2">
      <PanelHeader title="Broker Connection · Zerodha Kite" right={
        <span className={`flex items-center gap-1.5 text-[11px] font-mono ${connected ? "text-bull" : "text-slate-500"}`}>
          {connected ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
          {connected ? "LIVE / CONNECTED" : "NOT CONNECTED · DEMO DATA"}
        </span>} />
      {isLoading ? <Spinner /> : (
        <div className="p-4 space-y-4">
          <p className="text-xs text-slate-400 leading-relaxed">
            Kite access tokens expire daily (~06:00 IST), so a fresh login is required each trading day.
            Your API key/secret stay server-side. Step 1: open the Kite login. Step 2: after logging in,
            copy the <code className="text-cyan">request_token</code> from the redirected URL and paste it below.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <button data-testid="kite-login-btn" onClick={openLogin}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-mono rounded bg-cyan/10 text-cyan border border-cyan/30 hover:bg-cyan/20">
              <ExternalLink size={13} /> Open Zerodha Login
            </button>
            {connected && (
              <button data-testid="kite-logout-btn" onClick={() => logout.mutate()}
                className="px-3 py-2 text-xs font-mono rounded bg-bear/10 text-bear border border-bear/30 hover:bg-bear/20">
                Disconnect
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <input data-testid="kite-token-input" value={token} onChange={(e) => setToken(e.target.value)}
              placeholder="Paste request_token here"
              className="flex-1 bg-surface px-3 py-2 text-sm font-mono text-slate-100 rounded border border-surface-2 focus:border-cyan focus:outline-none" />
            <button data-testid="kite-connect-btn" onClick={() => token.trim() && connect.mutate(token.trim())}
              disabled={!token.trim() || connect.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-mono rounded bg-bull/15 text-bull border border-bull/30 hover:bg-bull/25 disabled:opacity-40">
              <Link2 size={13} /> {connect.isPending ? "Connecting…" : "Connect"}
            </button>
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            API key configured: {st?.api_key_present ? "yes" : "no"}
            {st?.login_time && ` · last login ${st.login_time}`}
          </div>
        </div>
      )}
    </Panel>
  );
};

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({ queryKey: ["settings"], queryFn: api.settings, retry: 1 });
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

      {isLoading ? <Spinner /> : (isError || !s) ? (
        <ErrorState title="Settings unavailable" hint="Could not load settings from the backend." error={error} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <KiteConnect />
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
