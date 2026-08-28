import { useState, useEffect, useCallback, useRef } from 'react';
import { marketAPI } from '../api/client';
import { useToast } from '../context/ToastContext';
import {
  TrendingUp, TrendingDown, Minus, Loader2, AlertCircle, Lightbulb,
  ShieldCheck, Database, Layers, Gauge, CheckCircle2,
} from 'lucide-react';

/* ── Helpers ────────────────────────────────────────────────────────────── */

function fmt(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function DataBadge({ source }) {
  if (source === 'verified') return <span className="badge-success text-[10px] py-0"><ShieldCheck className="w-3 h-3" /> Live verified</span>;
  if (source === 'reference') return <span className="badge-info text-[10px] py-0"><Database className="w-3 h-3" /> Reference</span>;
  return <span className="badge-neutral text-[10px] py-0">Unavailable</span>;
}

function Diff({ pct }) {
  if (pct == null || Number.isNaN(pct)) return <span className="text-surface-400 text-xs">—</span>;
  const up = pct > 0.05, down = pct < -0.05;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${up ? 'text-red-500' : down ? 'text-emerald-500' : 'text-surface-500'}`}>
      {up ? <TrendingUp className="w-3.5 h-3.5" /> : down ? <TrendingDown className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />}
      {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  );
}

function PositionIcon({ level }) {
  if (level === 'above_range') return <TrendingUp className="w-4 h-4 text-red-500" />;
  if (level === 'below_range') return <TrendingDown className="w-4 h-4 text-emerald-500" />;
  return <Minus className="w-4 h-4 text-primary-500" />;
}

/* ── Main Component ─────────────────────────────────────────────────────── */

export default function MarketIntelligence({ productId }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  const load = useCallback(async (pid) => {
    if (!pid) return;
    const s = ++seq.current;
    setLoading(true);
    try {
      const res = await marketAPI.analyze(pid);
      if (seq.current === s) setData(res.data);
    } catch (err) {
      if (seq.current === s) { setData(null); toast.error('Market intelligence failed', err.response?.data?.detail); }
    } finally { if (seq.current === s) setLoading(false); }
  }, [toast]);

  useEffect(() => {
    load(productId);
    return () => { seq.current += 1; };
  }, [productId, load]);

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="card">
        <div className="card-body flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if (!data) {
    return (
      <div className="card">
        <div className="card-body py-4 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          <p className="text-sm text-surface-600 dark:text-surface-400">Market intelligence unavailable for this product.</p>
        </div>
      </div>
    );
  }

  const rng = data.market?.range || {};
  const positioning = data.market?.positioning || {};
  const comps = data.competitors || {};
  const verified = data.verified_prices || {};
  const opportunity = data.pricing_opportunity || {};

  const hasLive = verified.available && verified.count > 0;
  const dataSource = hasLive ? 'verified' : (rng.source === 'reference' ? 'reference' : 'unavailable');

  /* ── Position text ── */
  const positionText = {
    above_range: 'Above comparable market range',
    below_range: 'Below comparable market range',
    within_range: 'Within comparable market range',
  }[positioning.level] || 'Position unknown';

  /* ── Top insight (first supported one) ── */
  const topInsight = (data.insights || []).find(i => i.support === 'high' || i.support === 'medium');

  return (
    <div className="space-y-4">
      <div className="card overflow-hidden">
        {/* ── Header ── */}
        <div className="card-header border-b border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-primary-500" />
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Market Intelligence</h3>
          </div>
          <DataBadge source={dataSource} />
        </div>

        {/* ── Market Snapshot (compact KPIs) ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-surface-200 dark:bg-surface-700">
          {[
            { label: 'Comparables', value: comps.found ?? 0, icon: Layers, sub: `${comps.with_reference_price ?? 0} with reference price` },
            { label: 'Verified Prices', value: verified.count ?? 0, icon: ShieldCheck, sub: hasLive ? `${fmt(verified.min)} – ${fmt(verified.max)}` : 'None available' },
            { label: 'Market Range', value: rng.low != null ? `${fmt(rng.low)} – ${fmt(rng.high)}` : '—', icon: Gauge, sub: rng.count ? `Based on ${rng.count} prices` : 'No data' },
            { label: 'vs Average', value: rng.diff_vs_avg_pct != null ? <Diff pct={rng.diff_vs_avg_pct} /> : '—', icon: TrendingUp, sub: rng.avg ? `Avg ${fmt(rng.avg)}` : 'Avg unavailable' },
          ].map((t) => (
            <div key={t.label} className="bg-white dark:bg-surface-800 p-4">
              <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-surface-400 font-medium">
                <t.icon className="w-3 h-3" /> {t.label}
              </p>
              <p className="text-lg font-bold text-surface-900 dark:text-white mt-1.5">{t.value}</p>
              <p className="text-[10px] text-surface-400 mt-0.5 truncate leading-relaxed">{t.sub}</p>
            </div>
          ))}
        </div>

        {/* ── Position + Opportunity (two columns) ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-surface-200 dark:divide-surface-700">
          {/* Price Position */}
          <div className="p-5">
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium mb-2.5">Price Position</p>
            <div className="flex items-center gap-2">
              <PositionIcon level={positioning.level} />
              <p className="text-sm font-semibold text-surface-900 dark:text-white">{positionText}</p>
            </div>
            {rng.avg != null && (
              <p className="text-[11px] text-surface-500 mt-2">
                Market average: <span className="font-medium text-surface-700 dark:text-surface-300">{fmt(rng.avg)}</span>
                <span className="text-surface-400 ml-1">({dataSource})</span>
              </p>
            )}
          </div>

          {/* Pricing Opportunity */}
          <div className="p-5">
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium mb-2.5">Recommendation</p>
            <p className="text-sm text-surface-900 dark:text-white leading-relaxed">
              {opportunity.text || 'No recommendation available.'}
            </p>
            {opportunity.basis && (
              <p className="text-[11px] text-surface-400 mt-2">
                Basis: {opportunity.basis}
                {opportunity.data_supported && <span className="text-emerald-500 ml-1">· data-supported</span>}
              </p>
            )}
          </div>
        </div>

        {/* ── Key Insight (compact) ── */}
        {topInsight && (
          <div className="px-5 pb-4">
            <div className="p-3.5 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
              <p className="text-[13px] text-primary-800 dark:text-primary-200 leading-relaxed">{topInsight.text}</p>
            </div>
          </div>
        )}

        {/* ── No verified prices notice (compact) ── */}
        {!hasLive && rng.source !== 'unavailable' && (
          <div className="px-5 pb-4">
            <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
              <p className="text-[11px] text-amber-700 dark:text-amber-300 leading-relaxed">
                No live verified prices — range above uses reference/catalog data, not live marketplace prices.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
