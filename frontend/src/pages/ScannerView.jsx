import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, ArrowUpDown, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, PanelHeader, ScoreBar, BiasBadge, Spinner, MockBadge } from "@/components/common";
import { inr, fmt, timeIST, modeLabel, MODES } from "@/lib/format";

const COLS = [
  { key: "rank", label: "#", align: "left" },
  { key: "symbol", label: "Symbol", align: "left" },
  { key: "price", label: "LTP", align: "right" },
  { key: "score", label: "Score", align: "left" },
  { key: "confidence", label: "Conf", align: "right" },
  { key: "bias", label: "Bias", align: "center" },
  { key: "trend", label: "Trend", align: "center" },
  { key: "rsi", label: "RSI", align: "right" },
  { key: "relative_volume", label: "R.Vol", align: "right" },
  { key: "sector", label: "Sector", align: "left" },
];

export default function ScannerView({ lockedMode }) {
  const [mode, setMode] = useState(lockedMode || "swing");
  const [sort, setSort] = useState({ key: "rank", dir: "asc" });
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("all");
  const [bias, setBias] = useState("all");

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["scan", mode],
    queryFn: () => api.scan(mode),
  });

  const rows = useMemo(() => {
    let r = data?.results ? [...data.results] : [];
    if (query) r = r.filter((x) => x.symbol.includes(query.toUpperCase()));
    if (sector !== "all") r = r.filter((x) => x.sector === sector);
    if (bias !== "all") r = r.filter((x) => x.bias === bias);
    r.sort((a, b) => {
      const va = a[sort.key], vb = b[sort.key];
      const cmp = typeof va === "string" ? String(va).localeCompare(String(vb)) : (va || 0) - (vb || 0);
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return r;
  }, [data, query, sector, bias, sort]);

  const sectors = useMemo(() => [...new Set((data?.results || []).map((r) => r.sector))].sort(), [data]);
  const toggleSort = (key) => setSort((s) => ({ key, dir: s.key === key && s.dir === "asc" ? "desc" : "asc" }));

  return (
    <div className="space-y-4" data-testid="scanner-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-100">
            {lockedMode ? `${modeLabel(mode)} Scanner` : "NIFTY 50 Scanner"}
          </h1>
          <p className="text-sm text-slate-500">Deterministic scoring first · AI explanation only for top finalists (cost control)</p>
        </div>
        <MockBadge />
      </div>

      <Panel>
        <div className="flex items-center gap-3 p-3 border-b border-surface-2 flex-wrap">
          {!lockedMode && (
            <div className="flex rounded overflow-hidden border border-surface-2" data-testid="scanner-mode-switch">
              {MODES.map((m) => (
                <button key={m.key} data-testid={`mode-${m.key}`} onClick={() => setMode(m.key)}
                  className={`px-3 py-1.5 text-xs font-mono ${mode === m.key ? "bg-cyan/15 text-cyan" : "text-slate-400 hover:text-slate-200"}`}>
                  {m.label}
                </button>
              ))}
            </div>
          )}
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input data-testid="scanner-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter symbol"
              className="w-36 bg-surface pl-8 pr-2 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none" />
          </div>
          <select data-testid="scanner-sector-filter" value={sector} onChange={(e) => setSector(e.target.value)}
            className="bg-surface px-2 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none text-slate-300">
            <option value="all">All Sectors</option>
            {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select data-testid="scanner-bias-filter" value={bias} onChange={(e) => setBias(e.target.value)}
            className="bg-surface px-2 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none text-slate-300">
            <option value="all">All Bias</option>
            <option value="bullish">Bullish</option>
            <option value="neutral">Neutral</option>
            <option value="bearish">Bearish</option>
          </select>
          <div className="flex-1" />
          <span className="text-[11px] font-mono text-slate-500">
            {data?.ai_finalists ?? 0} AI finalists · {rows.length}/{data?.count ?? 0} · {timeIST(data?.as_of)}
            {isFetching && " · refreshing…"}
          </span>
        </div>

        {isLoading ? <Spinner label="Scanning NIFTY 50…" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="scanner-table">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-surface-2">
                  {COLS.map((c) => (
                    <th key={c.key} onClick={() => toggleSort(c.key)}
                      className={`px-3 py-2 cursor-pointer hover:text-slate-300 select-none text-${c.align}`}
                      data-testid={`col-${c.key}`}>
                      <span className="inline-flex items-center gap-1">{c.label}<ArrowUpDown size={10} className="opacity-40" /></span>
                    </th>
                  ))}
                  <th className="px-3 py-2 text-left">Setup / AI</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {rows.map((r) => (
                  <tr key={r.symbol} className="border-b border-surface-2/60 hover:bg-surface-2/30" data-testid={`scan-row-${r.symbol}`}>
                    <td className="px-3 py-2 text-slate-600">{r.rank}</td>
                    <td className="px-3 py-2">
                      <Link to={`/stock-analysis?symbol=${r.symbol}&mode=${mode}`} className="text-slate-100 font-semibold hover:text-cyan">{r.symbol}</Link>
                    </td>
                    <td className="px-3 py-2 text-right text-slate-200">{inr(r.price)}</td>
                    <td className="px-3 py-2"><ScoreBar score={r.score} /></td>
                    <td className="px-3 py-2 text-right text-slate-300">{((r.confidence || 0) * 100).toFixed(0)}%</td>
                    <td className="px-3 py-2 text-center"><BiasBadge bias={r.bias} /></td>
                    <td className="px-3 py-2 text-center text-xs text-slate-400">{r.trend}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmt(r.rsi, 0)}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{fmt(r.relative_volume, 2)}×</td>
                    <td className="px-3 py-2 text-slate-400 font-sans text-xs">{r.sector}</td>
                    <td className="px-3 py-2 text-xs text-slate-400 max-w-xs truncate">
                      {r.ai_summary ? (
                        <span className="inline-flex items-center gap-1 text-ai"><Sparkles size={11} />{r.ai_summary.slice(0, 60)}…</span>
                      ) : r.trade_setup?.setup_validity === "valid" ? (
                        <span className="text-slate-400">{r.trade_setup.direction} · SL {inr(r.trade_setup.stop_loss, 0)} · T1 {inr(r.trade_setup.target_1, 0)}</span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
