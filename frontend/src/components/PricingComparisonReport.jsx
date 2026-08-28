import { useState, useEffect, useCallback, useRef } from 'react';
import { marketAPI } from '../api/client';
import { useToast } from '../context/ToastContext';
import {
  FileText, Loader2, AlertCircle, ShieldCheck, Database, Store,
  ExternalLink, TrendingUp, TrendingDown, Minus, Lightbulb,
  ChevronDown, BrainCircuit, Activity,
} from 'lucide-react';

/* ── Helpers ────────────────────────────────────────────────────────────── */

function fmt(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function DataBadge({ source }) {
  if (source === 'verified') return <span className="badge-success text-[10px] py-0"><ShieldCheck className="w-3 h-3" /> Live</span>;
  if (source === 'reference') return <span className="badge-info text-[10px] py-0"><Database className="w-3 h-3" /> Reference</span>;
  return <span className="badge-neutral text-[10px] py-0">Unavailable</span>;
}

function MatchBadge({ matchType }) {
  if (matchType === 'exact_product') return <span className="badge-success text-[10px] py-0">Exact</span>;
  if (matchType === 'exact_model') return <span className="badge-success text-[10px] py-0">Exact model</span>;
  if (matchType === 'close_match' || matchType === 'strong_spec') return <span className="badge-info text-[10px] py-0">Close</span>;
  return <span className="badge-neutral text-[10px] py-0">Comparable</span>;
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

function TrendIcon({ trend }) {
  if (trend === 'up') return <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />;
  if (trend === 'down') return <TrendingDown className="w-3.5 h-3.5 text-red-500" />;
  return <Minus className="w-3.5 h-3.5 text-surface-400" />;
}

/* ── Source Chips (compact, inline) ─────────────────────────────────────── */

function SourceChips({ sources }) {
  if (!sources?.length) return <span className="text-[10px] text-surface-400">No sources</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {sources.map((s) => {
        const name = s.marketplace || s.platform;
        const verified = (s.price_source || s.price_status) === 'verified' && s.price != null;
        return (
          <a key={name} href={s.url} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-100 dark:bg-surface-700/50 text-[10px] text-surface-600 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
             title={verified ? `${name}: ${fmt(s.price)}` : `${name}: Price unavailable`}>
            <Store className="w-2.5 h-2.5" />
            {name}
            {verified ? (
              <span className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400">{fmt(s.price)}</span>
            ) : (
              <span className="text-[9px] text-surface-400">unavail.</span>
            )}
          </a>
        );
      })}
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────────────────────── */

export default function PricingComparisonReport({ productId }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  const load = useCallback(async (pid) => {
    if (!pid) return;
    const s = ++seq.current;
    setLoading(true);
    try {
      const res = await marketAPI.report(pid, 30);
      if (seq.current === s) setData(res.data);
    } catch (err) {
      if (seq.current === s) { setData(null); toast.error('Report failed', err.response?.data?.detail); }
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
          <p className="text-sm text-surface-600 dark:text-surface-400">Pricing report unavailable for this product.</p>
        </div>
      </div>
    );
  }

  const p = data.product || {};
  const rng = data.market_price_range || {};
  const competitors = data.competitors || [];
  const recommendations = data.recommendations || [];
  const sourceLinks = data.source_links || [];
  const verified = data.verified_prices || {};
  const ai = data.ai_context || {};
  const hasLive = verified.available && verified.count > 0;

  /* ── Derived ── */
  const dataSource = hasLive ? 'verified' : (rng.source === 'reference' ? 'reference' : 'unavailable');
  const prices = competitors.map(c => c.reference_price || c.price).filter(Boolean);
  const marketLow = prices.length ? Math.min(...prices) : null;
  const marketHigh = prices.length ? Math.max(...prices) : null;
  const marketAvg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null;

  return (
    <div className="card overflow-hidden">
      {/* ── Header ── */}
      <div className="bg-gradient-to-r from-primary-50 to-transparent dark:from-primary-900/20 px-6 py-5 border-b border-surface-200 dark:border-surface-700">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-800/40">
              <FileText className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-surface-900 dark:text-white leading-snug">{p.name}</h3>
              <p className="text-xs text-surface-500 mt-0.5">{p.brand} · {p.category} · SKU {p.sku || '—'}</p>
            </div>
          </div>
          <DataBadge source={dataSource} />
        </div>
        <div className="mt-3 flex items-baseline gap-6">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">PricePilot Price</p>
            <p className="text-2xl font-bold text-primary-600 dark:text-primary-400 mt-1">{fmt(data.pricepilot_price)}</p>
          </div>
          {p.base_price && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Base Price</p>
              <p className="text-lg font-semibold text-surface-700 dark:text-surface-300 mt-1">{fmt(p.base_price)}</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div className="card-body space-y-6">

        {/* 1. Key Pricing Insight */}
        {data.key_pricing_insight && (
          <div className="flex items-start gap-2.5 p-4 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
            <Lightbulb className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm font-medium text-primary-800 dark:text-primary-200 leading-relaxed">
              {data.key_pricing_insight.length > 160
                ? data.key_pricing_insight.slice(0, 160).trim() + '…'
                : data.key_pricing_insight}
            </p>
          </div>
        )}

        {/* 2. Competitor Comparison Table */}
        {competitors.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <h4 className="text-sm font-semibold text-surface-900 dark:text-white">Competitor Products</h4>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-surface-100 dark:bg-surface-700 text-surface-500">{competitors.length}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-50 dark:bg-surface-800/50">
                    <th className="table-header text-left w-[35%]">Competitor Product</th>
                    <th className="table-header text-center w-[14%]">Match</th>
                    <th className="table-header text-right w-[16%]">Price</th>
                    <th className="table-header text-right w-[15%]">vs PricePilot</th>
                    <th className="table-header text-left w-[20%]">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                  {competitors.map((c, i) => {
                    const price = c.reference_price || c.price;
                    const srcs = c.platforms || [];
                    return (
                      <tr key={c.product_id || i} className="table-row">
                        <td className="py-3.5 pl-4">
                          <p className="text-sm font-medium text-surface-900 dark:text-white leading-snug">{c.name}</p>
                          <p className="text-[11px] text-surface-400 mt-0.5">{c.brand} · {c.category}</p>
                        </td>
                        <td className="py-3.5 text-center">
                          <MatchBadge matchType={c.match_type} />
                        </td>
                        <td className="py-3.5 text-right pr-4">
                          <p className="font-mono font-semibold text-sm text-surface-900 dark:text-white">{fmt(price)}</p>
                        </td>
                        <td className="py-3.5 text-right">
                          <Diff pct={c.price_difference_pct} />
                        </td>
                        <td className="py-3.5">
                          <SourceChips sources={srcs} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 3. Market Summary */}
        {marketLow != null && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Lowest', value: marketLow },
              { label: 'Average', value: marketAvg },
              { label: 'Highest', value: marketHigh },
              { label: 'PricePilot', value: data.pricepilot_price, highlight: true },
            ].map((t) => (
              <div key={t.label} className={`p-3.5 rounded-lg border ${t.highlight ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800' : 'bg-surface-50 dark:bg-surface-700/40 border-surface-200 dark:border-surface-700'}`}>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">{t.label}</p>
                <p className={`text-lg font-bold mt-1 ${t.highlight ? 'text-primary-600 dark:text-primary-400' : 'text-surface-900 dark:text-white'}`}>{fmt(t.value)}</p>
              </div>
            ))}
          </div>
        )}

        {/* 4. AI Context (compact, secondary) */}
        {ai.available && (
          <div className="p-5 rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/50">
            <div className="flex items-center gap-2 mb-4">
              <BrainCircuit className="w-4 h-4 text-surface-400" />
              <h4 className="text-xs font-semibold text-surface-600 dark:text-surface-400 uppercase tracking-wider">AI Insight</h4>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-5">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Suggested Price</p>
                <p className="text-xl font-bold text-surface-900 dark:text-white mt-1">{fmt(ai.suggested_price)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Confidence</p>
                <p className="text-xl font-bold text-surface-900 dark:text-white mt-1">{ai.confidence_score != null ? `${ai.confidence_score.toFixed(0)}%` : '—'}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Revenue Change</p>
                <p className={`text-xl font-bold mt-1 ${(ai.expected_revenue_change ?? 0) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {ai.expected_revenue_change != null ? `${ai.expected_revenue_change >= 0 ? '+' : ''}${ai.expected_revenue_change.toFixed(1)}%` : '—'}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Demand</p>
                <div className="flex items-center gap-1.5 mt-1">
                  <TrendIcon trend={ai.demand_trend} />
                  <span className="text-sm font-semibold text-surface-900 dark:text-white capitalize">{ai.demand_trend || '—'}</span>
                </div>
              </div>
            </div>
            {ai.integration && (
              <p className="mt-4 text-[11px] text-surface-500 dark:text-surface-400 border-t border-surface-200 dark:border-surface-700 pt-3 leading-relaxed">{ai.integration}</p>
            )}
          </div>
        )}

        {/* 5. Recommendation */}
        {recommendations.length > 0 && (
          <div className="space-y-2.5">
            {recommendations.map((rec, i) => (
              <div key={i} className="p-3.5 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700 flex items-start gap-3">
                <p className="text-sm text-surface-800 dark:text-surface-100 flex-1 leading-relaxed">{rec.text}</p>
                <span className={`badge text-[10px] py-0 flex-shrink-0 ${rec.kind === 'ai' ? 'badge-success' : rec.kind === 'market' ? 'badge-info' : 'badge-neutral'}`}>
                  {rec.kind === 'ai' ? 'AI' : rec.kind === 'market' ? 'Market' : 'Note'}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* 6. Source Links (collapsible) */}
        {sourceLinks.length > 0 && (
          <details className="group">
            <summary className="flex items-center gap-2 cursor-pointer text-[11px] text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 transition-colors select-none">
              <Store className="w-3.5 h-3.5" />
              <span>{sourceLinks.length} marketplace sources for "{p.name}"</span>
              <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
            </summary>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {sourceLinks.map((l) => (
                <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-surface-100 dark:bg-surface-700/50 border border-surface-200 dark:border-surface-600 text-[11px] font-medium text-surface-600 dark:text-surface-300 hover:border-primary-400 hover:text-primary-600 dark:hover:text-primary-300 transition-colors">
                  <Store className="w-3 h-3" />{l.label}
                  <ExternalLink className="w-2.5 h-2.5 opacity-40" />
                </a>
              ))}
            </div>
          </details>
        )}

        {/* 7. Data Status (compact) */}
        {!hasLive && (
          <div className="flex items-center gap-2 text-[11px] text-surface-400 pt-2 border-t border-surface-100 dark:border-surface-800">
            <DataBadge source={dataSource} />
            <span>· Reference/catalog prices — not live marketplace data</span>
          </div>
        )}
      </div>
    </div>
  );
}
