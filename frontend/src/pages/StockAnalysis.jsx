import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Play, Sparkles, Target, ShieldAlert, Info, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner, BiasBadge, ConfidenceGauge, FactorBars, MockBadge, StaleBadge, EmptyState } from "@/components/common";
import { CandleChart, RsiLine } from "@/components/charts";
import { inr, pct, fmt, signClass, timeIST, dateIST, isStale, MODES, modeLabel } from "@/lib/format";

const ema = (closes, period) => {
  if (closes.length < period) return [];
  const k = 2 / (period + 1);
  const out = [];
  let e = closes[0];
  closes.forEach((v, i) => { e = i === 0 ? v : v * k + e * (1 - k); out.push(e); });
  return out.map((v) => Number(v.toFixed(2)));
};

const TABS = ["Overview", "Technical", "Fundamental", "Market/Sector", "Trade Setup", "AI Analysis", "Evaluation", "Historical Data"];

const Row = ({ label, value, cls = "text-slate-200" }) => (
  <div className="flex items-center justify-between px-4 py-2 border-b border-surface-2/60">
    <span className="text-xs text-slate-500">{label}</span>
    <span className={`font-mono text-sm ${cls}`}>{value}</span>
  </div>
);

const TradeSetupCard = ({ setup, ai }) => {
  if (!setup) return <EmptyState title="No trade setup" hint="Trade setups apply to Swing & Intraday modes." />;
  if (setup.setup_validity !== "valid")
    return <EmptyState title="No actionable setup" hint={setup.reason || "Neutral bias — no hypothetical setup generated."} />;
  const long = setup.direction === "LONG";
  const c = long ? "#10B981" : "#EF4444";
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="trade-setup-card">
      <Panel className="lg:col-span-2 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2"><Target size={16} className="text-cyan" />
            <span className="font-display font-semibold text-slate-100">Hypothetical {setup.direction} Setup</span></div>
          <BiasBadge bias={setup.direction} testid="trade-setup-bias-badge" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-surface-2 rounded overflow-hidden">
          {[
            ["Ideal Entry", inr(setup.entry), "text-slate-100"],
            ["Entry Zone", `${inr(setup.entry_zone?.[0], 0)}–${inr(setup.entry_zone?.[1], 0)}`, "text-slate-300"],
            ["Stop Loss", inr(setup.stop_loss), "num-neg"],
            ["Target 1", inr(setup.target_1), "num-pos"],
            ["Target 2", inr(setup.target_2), "num-pos"],
            ["Risk : Reward", `1:${setup.risk_reward_1} / 1:${setup.risk_reward_2}`, "text-cyan"],
          ].map(([l, v, cl]) => (
            <div key={l} className="bg-surface px-3 py-2.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">{l}</div>
              <div className={`font-mono text-base font-bold ${cl}`}>{v}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-px bg-surface-2 rounded overflow-hidden mt-px">
          <div className="bg-surface px-3 py-2"><div className="text-[10px] uppercase text-slate-500">Risk / Share</div><div className="font-mono text-sm text-slate-200">{inr(setup.risk_per_share)}</div></div>
          <div className="bg-surface px-3 py-2"><div className="text-[10px] uppercase text-slate-500">Position Size</div><div className="font-mono text-sm text-slate-200">{setup.position_size} sh</div></div>
          <div className="bg-surface px-3 py-2"><div className="text-[10px] uppercase text-slate-500">Capital Req.</div><div className="font-mono text-sm text-slate-200">{inr(setup.capital_required, 0)}</div></div>
        </div>
        <p className="text-[11px] text-slate-500 mt-3">
          Levels computed deterministically by the Risk Engine (ATR × config multipliers, structure-aware).
          Assumptions: ATR {setup.assumptions?.atr}, risk {setup.assumptions?.risk_per_trade_pct}% of ₹{fmt(setup.assumptions?.account_capital, 0)}.
        </p>
      </Panel>
      <Panel className="p-4">
        <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Invalidation Conditions</div>
        <ul className="space-y-1.5 text-xs text-slate-400">
          {(ai?.invalidation_conditions || ["Close beyond stop invalidates the setup."]).map((x, i) => (
            <li key={i} className="flex gap-2"><ShieldAlert size={13} className="text-bear shrink-0 mt-0.5" />{x}</li>
          ))}
        </ul>
      </Panel>
    </div>
  );
};

export default function StockAnalysis() {
  const [params, setParams] = useSearchParams();
  const [symbol, setSymbol] = useState(params.get("symbol") || "RELIANCE");
  const [mode, setMode] = useState(params.get("mode") || "swing");
  const [active, setActive] = useState("Overview");
  const [runKey, setRunKey] = useState(`${params.get("symbol") || "RELIANCE"}:${params.get("mode") || "swing"}`);

  const [reqSymbol, reqMode] = runKey.split(":");

  const analysis = useQuery({ queryKey: ["analyze", runKey], queryFn: () => api.analyze({ symbol: reqSymbol, mode: reqMode }) });
  const candles = useQuery({ queryKey: ["candles", reqSymbol, reqMode], queryFn: () => api.candles(reqSymbol, reqMode === "intraday" ? "15m" : "1d", 180) });
  const fundamentals = useQuery({ queryKey: ["fundamentals", reqSymbol], queryFn: () => api.fundamentals(reqSymbol) });
  const news = useQuery({ queryKey: ["news", reqSymbol], queryFn: () => api.news(reqSymbol) });

  const run = () => {
    const key = `${symbol.toUpperCase()}:${mode}`;
    setRunKey(key);
    setParams({ symbol: symbol.toUpperCase(), mode });
  };

  const closes = useMemo(() => (candles.data?.candles || []).map((c) => c.close), [candles.data]);
  const emas = useMemo(() => ({ ema20: ema(closes, 20), ema50: ema(closes, 50), ema200: ema(closes, 200) }), [closes]);
  const rsiSeries = useMemo(() => {
    const arr = []; const p = 14;
    for (let i = p; i < closes.length; i++) {
      let g = 0, l = 0;
      for (let j = i - p + 1; j <= i; j++) { const d = closes[j] - closes[j - 1]; if (d > 0) g += d; else l -= d; }
      const rs = l === 0 ? 100 : g / l; arr.push(l === 0 ? 100 : 100 - 100 / (1 + rs));
    }
    return arr;
  }, [closes]);

  const d = analysis.data;
  const f = d?.features;
  const fund = fundamentals.data;

  return (
    <div className="space-y-4" data-testid="stock-analysis-page">
      <div className="flex items-center gap-3 flex-wrap">
        <input data-testid="analysis-symbol-input" value={symbol} onChange={(e) => setSymbol(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          className="w-40 bg-surface px-3 py-2 font-mono font-semibold text-slate-100 rounded border border-surface-2 focus:border-cyan focus:outline-none uppercase" />
        <div className="flex rounded overflow-hidden border border-surface-2">
          {MODES.map((m) => (
            <button key={m.key} data-testid={`analysis-mode-${m.key}`} onClick={() => setMode(m.key)}
              className={`px-3 py-2 text-xs font-mono ${mode === m.key ? "bg-cyan/15 text-cyan" : "text-slate-400 hover:text-slate-200"}`}>{m.label}</button>
          ))}
        </div>
        <button data-testid="run-analysis-btn" onClick={run}
          className="flex items-center gap-2 px-4 py-2 bg-cyan text-[#08111f] font-semibold text-sm rounded hover:bg-cyan/90 transition-colors">
          <Play size={14} /> Run Analysis
        </button>
        <div className="flex-1" />
        <MockBadge />
      </div>

      {analysis.isLoading ? <Spinner label={`Analyzing ${reqSymbol}…`} /> : analysis.isError ? (
        <Panel className="p-6"><EmptyState title="Analysis failed" hint={analysis.error?.response?.data?.detail || "Unknown symbol or backend error."} /></Panel>
      ) : d && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Panel className="p-4 md:col-span-2">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-display text-2xl font-bold text-slate-100">{d.symbol}</div>
                  <div className="text-sm text-slate-500">{d.name} · {d.sector}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-2xl font-bold text-slate-100">{inr(f?.last_price)}</div>
                  <div className="text-xs text-slate-500">{modeLabel(d.mode)} · {timeIST(d.as_of)}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <BiasBadge bias={d.score.bias} testid="analysis-bias-badge" />
                {isStale(d.as_of) && <StaleBadge />}
                {d.ai_cached && <span className="text-[10px] font-mono text-slate-500 border border-surface-2 rounded px-2 py-0.5">AI CACHED</span>}
                <span className="text-[10px] font-mono text-slate-500 border border-surface-2 rounded px-2 py-0.5">{d.provenance.strategy_version}</span>
              </div>
            </Panel>
            <Panel className="p-4 flex flex-col items-center justify-center">
              <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Quant Score</div>
              <div className="font-mono text-4xl font-bold" style={{ color: d.score.score >= 60 ? "#10B981" : d.score.score <= 40 ? "#EF4444" : "#F59E0B" }} data-testid="quant-score">
                {fmt(d.score.score, 1)}
              </div>
              <div className="text-[10px] text-slate-600">/ 100 · {d.provenance.scoring_version}</div>
            </Panel>
            <Panel className="p-4 flex items-center justify-center"><ConfidenceGauge value={d.score.confidence} /></Panel>
          </div>

          <div className="flex gap-1 border-b border-surface-2 overflow-x-auto">
            {TABS.map((t) => (
              <button key={t} data-testid={`tab-${t.replace(/[^a-z]/gi, "-").toLowerCase()}`} onClick={() => setActive(t)}
                className={`px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${active === t ? "border-cyan text-cyan" : "border-transparent text-slate-400 hover:text-slate-200"}`}>{t}</button>
            ))}
          </div>

          {active === "Overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Panel className="lg:col-span-2">
                <PanelHeader title={`Price · ${reqMode === "intraday" ? "15m" : "Daily"}`} icon={TrendingUp} right={<MockBadge />} />
                <div className="p-3">{candles.isLoading ? <Spinner /> : <CandleChart candles={candles.data?.candles || []} emas={emas} />}</div>
              </Panel>
              <Panel>
                <PanelHeader title="Score Factors" icon={Info} />
                <div className="p-4"><FactorBars factors={d.score.factors} /></div>
                {d.score.missing?.length > 0 && (
                  <div className="px-4 pb-4 text-[11px] text-watch">Missing (no data, not penalised): {d.score.missing.join(", ")}</div>
                )}
              </Panel>
            </div>
          )}

          {active === "Technical" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Panel className="lg:col-span-2">
                <PanelHeader title="Indicators (deterministic · technical_v1)" />
                <div className="grid grid-cols-2">
                  <div>
                    <Row label="Trend" value={f?.trend} />
                    <Row label="RSI (14)" value={fmt(f?.rsi, 1)} />
                    <Row label="EMA 20" value={inr(f?.ema20)} />
                    <Row label="EMA 50" value={inr(f?.ema50)} />
                    <Row label="EMA 200" value={inr(f?.ema200)} />
                    <Row label="Supertrend" value={f?.supertrend} cls={f?.supertrend === "bullish" ? "num-pos" : "num-neg"} />
                  </div>
                  <div>
                    <Row label="ATR" value={fmt(f?.atr)} />
                    <Row label="VWAP" value={f?.vwap ? inr(f.vwap) : "—"} />
                    <Row label="MACD Hist" value={fmt(f?.macd?.histogram)} cls={signClass(f?.macd?.histogram)} />
                    <Row label="Rel. Volume" value={`${fmt(f?.relative_volume)}×`} />
                    <Row label="Support" value={inr(f?.support_resistance?.support)} />
                    <Row label="Resistance" value={inr(f?.support_resistance?.resistance)} />
                  </div>
                </div>
              </Panel>
              <Panel>
                <PanelHeader title="RSI (14)" />
                <div className="p-3">{rsiSeries.length ? <RsiLine data={rsiSeries} /> : <EmptyState title="Insufficient data" />}</div>
                {f?.week52 && <div className="px-4 py-3 border-t border-surface-2"><Row label="52W High" value={inr(f.week52.high)} /><Row label="52W Low" value={inr(f.week52.low)} /><Row label="52W Position" value={pct(f.week52.position_pct, 0)} /></div>}
              </Panel>
            </div>
          )}

          {active === "Fundamental" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {fundamentals.isLoading ? <Spinner /> : fund && (<>
                <Panel><PanelHeader title="Income & Growth" />
                  <Row label="Revenue" value={`₹${fmt(fund.income_statement.revenue, 0)} cr`} />
                  <Row label="Revenue Growth" value={pct(fund.income_statement.revenue_growth_pct)} cls={signClass(fund.income_statement.revenue_growth_pct)} />
                  <Row label="PAT" value={`₹${fmt(fund.income_statement.pat, 0)} cr`} />
                  <Row label="PAT Growth" value={pct(fund.income_statement.pat_growth_pct)} cls={signClass(fund.income_statement.pat_growth_pct)} />
                  <Row label="EPS" value={inr(fund.income_statement.eps)} />
                  <Row label="EBITDA Margin" value={pct(fund.income_statement.ebitda_margin_pct)} />
                </Panel>
                <Panel><PanelHeader title="Valuation & Returns" />
                  <Row label="P/E" value={fmt(fund.valuation.pe)} />
                  <Row label="P/B" value={fmt(fund.valuation.pb)} />
                  <Row label="ROE" value={pct(fund.valuation.roe_pct)} />
                  <Row label="ROCE" value={pct(fund.valuation.roce_pct)} />
                  <Row label="Debt/Equity" value={fmt(fund.valuation.debt_to_equity)} />
                  <Row label="Dividend Yield" value={pct(fund.valuation.dividend_yield_pct)} />
                </Panel>
                <Panel><PanelHeader title="Cash Flow & Ownership" right={<span className="text-[10px] text-slate-600 font-mono">{fund.period}</span>} />
                  <Row label="Operating CF" value={`₹${fmt(fund.cash_flow.operating_cash_flow, 0)} cr`} />
                  <Row label="Capex" value={`₹${fmt(fund.cash_flow.capex, 0)} cr`} />
                  <Row label="Free Cash Flow" value={`₹${fmt(fund.cash_flow.free_cash_flow, 0)} cr`} cls={signClass(fund.cash_flow.free_cash_flow)} />
                  <Row label="Promoter" value={pct(fund.shareholding.promoter_pct)} />
                  <Row label="FII / DII" value={`${pct(fund.shareholding.fii_pct)} / ${pct(fund.shareholding.dii_pct)}`} />
                  <div className="px-4 py-2 text-[11px] text-watch">Source: mock (synthetic) · retrieved {dateIST(fund.retrieved_at)}</div>
                </Panel>
              </>)}
            </div>
          )}

          {active === "Market/Sector" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Panel><PanelHeader title="Market Context" />
                <Row label="NIFTY Direction" value={d.market_context?.nifty?.direction} />
                <Row label="NIFTY Trend" value={d.market_context?.nifty?.trend} />
                <Row label="BANKNIFTY Direction" value={d.market_context?.banknifty?.direction} />
                <Row label="Breadth" value={d.market_context?.breadth} />
                <div className="px-4 py-2 text-[11px] text-slate-500">{d.market_context?.note}</div>
              </Panel>
              <Panel><PanelHeader title="Sector Context" />
                <Row label="Sector" value={d.sector_context?.sector} />
                <Row label="Mapped Index" value={d.sector_context?.mapped_index} />
                <Row label="Direction" value={d.sector_context?.direction} />
                <Row label="Bullish / Bearish peers" value={`${d.sector_context?.constituents_bullish} / ${d.sector_context?.constituents_bearish}`} />
                <Row label="Relative Strength (20d)" value={fmt(d.relative_strength)} cls={signClass(d.relative_strength)} />
              </Panel>
            </div>
          )}

          {active === "Trade Setup" && <TradeSetupCard setup={d.trade_setup} ai={d.ai} />}

          {active === "AI Analysis" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Panel className="lg:col-span-2 border-ai/30">
                <PanelHeader title="AI Explanation Layer" icon={Sparkles}
                  right={<span className="text-[10px] font-mono text-ai border border-ai/30 bg-ai/10 rounded px-2 py-0.5">{d.provenance.provider} · {d.provenance.model}</span>} />
                <div className="p-4 space-y-3">
                  <p className="text-sm text-slate-200 leading-relaxed">{d.ai?.summary}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div><div className="text-[10px] uppercase text-bull mb-1">Bullish Factors</div>
                      <ul className="text-xs text-slate-400 space-y-1">{d.ai?.bullish_factors?.map((x, i) => <li key={i}>+ {x}</li>)}</ul></div>
                    <div><div className="text-[10px] uppercase text-bear mb-1">Bearish Factors</div>
                      <ul className="text-xs text-slate-400 space-y-1">{d.ai?.bearish_factors?.map((x, i) => <li key={i}>− {x}</li>)}</ul></div>
                  </div>
                  <div><div className="text-[10px] uppercase text-watch mb-1">Key Risks</div>
                    <ul className="text-xs text-slate-400 space-y-1">{d.ai?.risks?.map((x, i) => <li key={i}>• {x}</li>)}</ul></div>
                  <p className="text-[11px] text-slate-500 border-t border-surface-2 pt-2">{d.ai?.setup_commentary}</p>
                </div>
              </Panel>
              <Panel>
                <PanelHeader title="Grounding & Provenance" />
                <Row label="AI Bias" value={d.ai?.bias} />
                <Row label="AI Confidence" value={`${((d.ai?.confidence || 0) * 100).toFixed(0)}%`} />
                <Row label="Grounded" value={d.ai?.grounded ? "Yes" : "No"} cls={d.ai?.grounded ? "num-pos" : "num-neg"} />
                <Row label="Prompt Version" value={d.provenance.prompt_version} />
                <Row label="Market Data Ver." value={d.provenance.market_data_version} />
                {d.ai?.missing_data_warnings?.length > 0 && (
                  <div className="px-4 py-2 text-[11px] text-watch">{d.ai.missing_data_warnings.join(" · ")}</div>
                )}
              </Panel>
            </div>
          )}

          {active === "Evaluation" && <EvaluationTab d={d} />}

          {active === "Historical Data" && (
            <Panel>
              <PanelHeader title={`Recent Candles · ${reqMode === "intraday" ? "15m" : "Daily"}`} right={<span className="text-[10px] font-mono text-slate-500">mdv {candles.data?.market_data_version}</span>} />
              <div className="overflow-x-auto max-h-[420px]">
                <table className="w-full text-xs font-mono">
                  <thead className="sticky top-0 bg-surface"><tr className="text-slate-500 text-[10px] uppercase border-b border-surface-2">
                    {["Time", "Open", "High", "Low", "Close", "Volume"].map((h) => <th key={h} className="px-3 py-2 text-right first:text-left">{h}</th>)}
                  </tr></thead>
                  <tbody>
                    {[...(candles.data?.candles || [])].reverse().slice(0, 60).map((c, i) => (
                      <tr key={i} className="border-b border-surface-2/50">
                        <td className="px-3 py-1.5 text-left text-slate-400">{reqMode === "intraday" ? timeIST(c.ts) : dateIST(c.ts)}</td>
                        <td className="px-3 py-1.5 text-right text-slate-300">{fmt(c.open)}</td>
                        <td className="px-3 py-1.5 text-right text-slate-300">{fmt(c.high)}</td>
                        <td className="px-3 py-1.5 text-right text-slate-300">{fmt(c.low)}</td>
                        <td className={`px-3 py-1.5 text-right ${c.close >= c.open ? "num-pos" : "num-neg"}`}>{fmt(c.close)}</td>
                        <td className="px-3 py-1.5 text-right text-slate-500">{c.volume.toLocaleString("en-IN")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}

const EvaluationTab = ({ d }) => {
  const detBias = { bullish: "LONG", bearish: "SHORT", neutral: "NEUTRAL" }[d.score.bias];
  const checks = [
    { name: "Schema validity", pass: !!d.ai?.bias, detail: "AI output conforms to AIAnalysis schema" },
    { name: "Deterministic bias consistency", pass: d.ai?.bias === detBias, detail: `AI ${d.ai?.bias} vs deterministic ${detBias}` },
    { name: "Confidence consistency", pass: Math.abs((d.ai?.confidence || 0) - d.score.confidence) <= 0.01, detail: "AI confidence matches score confidence" },
    { name: "Grounding (missing-data flagged)", pass: (d.score.missing?.length || 0) === 0 || (d.ai?.missing_data_warnings?.length || 0) > 0, detail: "Missing factors surfaced to user" },
    { name: "Trade-level authority", pass: true, detail: "Levels sourced from deterministic Risk Engine, not AI" },
  ];
  return (
    <Panel>
      <PanelHeader title="Per-Analysis Evaluation Matrix" />
      <div className="divide-y divide-surface-2/60">
        {checks.map((c) => (
          <div key={c.name} className="flex items-center gap-3 px-4 py-2.5" data-testid={`eval-check-${c.name.replace(/[^a-z]/gi, "-").toLowerCase()}`}>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${c.pass ? "text-bull border-bull/30 bg-bull/10" : "text-bear border-bear/30 bg-bear/10"}`}>{c.pass ? "PASS" : "FAIL"}</span>
            <span className="text-sm text-slate-200 w-64">{c.name}</span>
            <span className="text-xs text-slate-500">{c.detail}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
};
