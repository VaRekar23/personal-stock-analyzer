import React, { useMemo, useState } from "react";
import { fmt, timeIST } from "@/lib/format";

// Lightweight dependency-free candlestick chart (SVG) with EMA overlays.
export const CandleChart = ({ candles = [], emas = {}, height = 340, showVolume = true }) => {
  const [hover, setHover] = useState(null);
  const W = 1000;
  const priceH = showVolume ? height * 0.76 : height;
  const volH = height - priceH;
  const padR = 56;
  const plotW = W - padR;

  const { min, max, vmax } = useMemo(() => {
    if (!candles.length) return { min: 0, max: 1, vmax: 1 };
    let mn = Infinity, mx = -Infinity, vm = 0;
    candles.forEach((c) => { mn = Math.min(mn, c.low); mx = Math.max(mx, c.high); vm = Math.max(vm, c.volume); });
    const pad = (mx - mn) * 0.06;
    return { min: mn - pad, max: mx + pad, vmax: vm };
  }, [candles]);

  if (!candles.length) return <div className="text-slate-500 text-sm py-10 text-center">No chart data</div>;

  const n = candles.length;
  const step = plotW / n;
  const bodyW = Math.max(1.2, step * 0.6);
  const yToPx = (p) => priceH - ((p - min) / (max - min)) * (priceH - 10) - 5;

  const emaPath = (arr) =>
    arr && arr.length
      ? arr.map((v, i) => `${i === 0 ? "M" : "L"} ${i * step + step / 2} ${yToPx(v)}`).join(" ")
      : "";

  const gridLines = 4;

  return (
    <div className="w-full select-none">
      <svg viewBox={`0 0 ${W} ${height}`} width="100%" height={height} preserveAspectRatio="none"
        onMouseLeave={() => setHover(null)}>
        {/* grid + price axis */}
        {Array.from({ length: gridLines + 1 }).map((_, i) => {
          const p = min + ((max - min) * i) / gridLines;
          const y = yToPx(p);
          return (
            <g key={i}>
              <line x1="0" x2={plotW} y1={y} y2={y} stroke="#1E293B" strokeWidth="1" />
              <text x={plotW + 6} y={y + 3} fill="#64748B" fontSize="11" fontFamily="JetBrains Mono">{fmt(p, 0)}</text>
            </g>
          );
        })}
        {/* candles */}
        {candles.map((c, i) => {
          const x = i * step + step / 2;
          const up = c.close >= c.open;
          const col = up ? "#10B981" : "#EF4444";
          const yO = yToPx(c.open), yC = yToPx(c.close);
          return (
            <g key={i} onMouseEnter={() => setHover({ ...c, i })}>
              <rect x={i * step} y="0" width={step} height={priceH} fill="transparent" />
              <line x1={x} x2={x} y1={yToPx(c.high)} y2={yToPx(c.low)} stroke={col} strokeWidth="1" />
              <rect x={x - bodyW / 2} y={Math.min(yO, yC)} width={bodyW}
                height={Math.max(1, Math.abs(yC - yO))} fill={col} />
            </g>
          );
        })}
        {/* EMA overlays */}
        {emas.ema20 && <path d={emaPath(emas.ema20)} fill="none" stroke="#38BDF8" strokeWidth="1.5" opacity="0.9" />}
        {emas.ema50 && <path d={emaPath(emas.ema50)} fill="none" stroke="#F59E0B" strokeWidth="1.5" opacity="0.9" />}
        {emas.ema200 && <path d={emaPath(emas.ema200)} fill="none" stroke="#A855F7" strokeWidth="1.5" opacity="0.8" />}
        {/* volume */}
        {showVolume && candles.map((c, i) => {
          const x = i * step;
          const h = (c.volume / vmax) * (volH - 6);
          const up = c.close >= c.open;
          return <rect key={i} x={x + step * 0.15} y={height - h} width={step * 0.7} height={h}
            fill={up ? "#10B981" : "#EF4444"} opacity="0.28" />;
        })}
        {hover && (
          <line x1={hover.i * step + step / 2} x2={hover.i * step + step / 2} y1="0" y2={height}
            stroke="#38BDF8" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
        )}
      </svg>
      <div className="flex items-center justify-between mt-2 text-[11px] font-mono">
        <div className="flex gap-3">
          <span className="text-cyan">EMA20</span>
          <span className="text-watch">EMA50</span>
          <span className="text-ai">EMA200</span>
        </div>
        {hover && (
          <div className="text-slate-400 flex gap-3">
            <span>{timeIST(hover.ts)}</span>
            <span>O {fmt(hover.open)}</span>
            <span>H {fmt(hover.high)}</span>
            <span>L {fmt(hover.low)}</span>
            <span className={hover.close >= hover.open ? "num-pos" : "num-neg"}>C {fmt(hover.close)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export const Sparkline = ({ data = [], color = "#38BDF8", width = 120, height = 34 }) => {
  if (!data.length) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const step = width / (data.length - 1 || 1);
  const y = (v) => height - ((v - min) / (max - min || 1)) * (height - 4) - 2;
  const d = data.map((v, i) => `${i === 0 ? "M" : "L"} ${i * step} ${y(v)}`).join(" ");
  return (
    <svg width={width} height={height}>
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
};

export const RsiLine = ({ data = [], height = 90 }) => {
  const W = 1000, padR = 56, plotW = W - padR;
  if (!data.length) return null;
  const step = plotW / data.length;
  const y = (v) => height - (v / 100) * (height - 8) - 4;
  const d = data.map((v, i) => `${i === 0 ? "M" : "L"} ${i * step + step / 2} ${y(v)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${height}`} width="100%" height={height} preserveAspectRatio="none">
      {[30, 50, 70].map((lvl) => (
        <g key={lvl}>
          <line x1="0" x2={plotW} y1={y(lvl)} y2={y(lvl)} stroke="#1E293B" strokeDasharray={lvl === 50 ? "" : "3 3"} />
          <text x={plotW + 6} y={y(lvl) + 3} fill="#64748B" fontSize="10" fontFamily="JetBrains Mono">{lvl}</text>
        </g>
      ))}
      <path d={d} fill="none" stroke="#38BDF8" strokeWidth="1.5" />
    </svg>
  );
};
