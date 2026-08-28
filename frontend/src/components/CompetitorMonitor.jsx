import { useState, useEffect, useCallback, useRef } from 'react';
import { competitorAPI } from '../api/client';
import { useToast } from '../context/ToastContext';
import ProductSearchSelect from './ProductSearchSelect';
import MarketIntelligence from './MarketIntelligence';
import PricingComparisonReport from './PricingComparisonReport';
import {
  Store, ExternalLink, Loader2, AlertCircle,
  ShieldCheck, Database, Tag, TrendingUp, TrendingDown, Minus,
  Info, Globe, Package, Crosshair, Layers, BadgeCheck,
  ChevronDown, ChevronUp,
} from 'lucide-react';

/* ── Helpers ────────────────────────────────────────────────────────────── */

function fmt(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function PriceBadge({ status }) {
  if (status === 'verified') return <span className="badge-success text-[10px] py-0"><ShieldCheck className="w-3 h-3" /> Live</span>;
  if (status === 'reference') return <span className="badge-info text-[10px] py-0"><Database className="w-3 h-3" /> Reference</span>;
  return <span className="badge-neutral text-[10px] py-0">Unavailable</span>;
}

function MatchBadge({ matchType }) {
  if (matchType === 'exact_product') return <span className="badge-success text-[10px] py-0"><BadgeCheck className="w-3 h-3" /> Exact</span>;
  if (matchType === 'exact_model') return <span className="badge-success text-[10px] py-0"><Crosshair className="w-3 h-3" /> Exact model</span>;
  if (matchType === 'close_match' || matchType === 'strong_spec') return <span className="badge-info text-[10px] py-0"><Tag className="w-3 h-3" /> Close</span>;
  return <span className="badge-neutral text-[10px] py-0"><Layers className="w-3 h-3" /> Comparable</span>;
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

function Specs({ specs }) {
  const entries = Object.entries(specs || {});
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {entries.slice(0, 4).map(([k, v]) => (
        <span key={k} className="px-1.5 py-0.5 rounded bg-surface-100 dark:bg-surface-700 text-[9px] font-mono text-surface-500 dark:text-surface-400">
          {k.replace(/_/g, ' ')}: {v}
        </span>
      ))}
    </div>
  );
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
             className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-100 dark:bg-surface-700/50 text-[10px] text-surface-600 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors group"
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

/* ── Source Links (full, for collapsible section) ────────────────────────── */

function SourceLinks({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {sources.map((s) => {
        const name = s.marketplace || s.platform;
        const verified = (s.price_source || s.price_status) === 'verified' && s.price != null;
        return (
          <a key={name} href={s.url} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-surface-100 dark:bg-surface-700/50 border border-surface-200 dark:border-surface-600 text-[11px] font-medium text-surface-700 dark:text-surface-300 hover:border-primary-400 hover:text-primary-600 dark:hover:text-primary-300 transition-colors"
             title={s.note}>
            <Store className="w-3 h-3" />
            {name}
            <ExternalLink className="w-2.5 h-2.5 opacity-40" />
            {verified ? (
              <span className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400 ml-0.5">{fmt(s.price)}</span>
            ) : (
              <span className="text-[9px] text-surface-400 ml-0.5">unavailable</span>
            )}
          </a>
        );
      })}
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────────────────────── */

export default function CompetitorMonitor({ selectedId: externalSelectedId, onSelectProduct }) {
  const toast = useToast();
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [showSources, setShowSources] = useState(false);
  const seq = useRef(0);

  /* Skeleton loader for competitive table rows */
  function TableSkeleton({ rows = 4 }) {
    return (
      <div className="space-y-3 p-5">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="skeleton h-4 w-48 rounded" />
            <div className="skeleton h-4 w-16 rounded ml-auto" />
            <div className="skeleton h-4 w-12 rounded" />
            <div className="skeleton h-4 w-20 rounded" />
          </div>
        ))}
      </div>
    );
  }

  useEffect(() => {
    if (externalSelectedId != null && externalSelectedId !== selectedId) setSelectedId(externalSelectedId);
  }, [externalSelectedId]); // eslint-disable-line

  const load = useCallback(async (pid) => {
    if (!pid) return;
    const s = ++seq.current;
    setLoading(true); setError(null);
    try {
      const res = await competitorAPI.analyze(pid);
      if (seq.current === s) setData(res.data);
    } catch (err) {
      if (seq.current === s) { setData(null); setError(err.response?.data?.detail || 'Analysis failed'); }
      toast.error('Competitor analysis failed', err.response?.data?.detail);
    } finally { if (seq.current === s) setLoading(false); }
  }, [toast]);

  useEffect(() => { if (selectedId) load(selectedId); }, [selectedId, load]);

  const handleProductChange = (product) => {
    if (!product) return;
    setSelectedId(product.id);
    onSelectProduct?.(product);
  };

  const p = data?.product;
  const exact = data?.exact_matches || [];
  const comps = data?.comparable_products || [];
  const allCompetitors = [...exact, ...comps];
  const sources = data?.selected_product_sources || [];

  /* ── Derived market stats ── */
  const prices = allCompetitors.map(c => c.price ?? c.reference_price).filter(Boolean);
  const marketLow = prices.length ? Math.min(...prices) : null;
  const marketHigh = prices.length ? Math.max(...prices) : null;
  const marketAvg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null;
  const ourPrice = p?.current_price;

  return (
    <div className="space-y-5">

      {/* ── Product Search ── */}
      <div className="card">
        <div className="card-body py-4">
          <label className="label mb-1">Analyze competitor products</label>
          <ProductSearchSelect value={selectedId} onSelect={handleProductChange}
            placeholder="Search by name, brand, category or SKU…" />
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
          <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          <p className="text-sm text-primary-700 dark:text-primary-300">Analyzing competitor products…</p>
        </div>
      )}

      {/* ── Selected Product Card ── */}
      {p && !loading && (
        <div className="card overflow-hidden">
          <div className="bg-gradient-to-r from-primary-50 to-transparent dark:from-primary-900/20 px-5 py-4 border-b border-surface-200 dark:border-surface-700">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-800/40">
                  <Package className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-surface-900 dark:text-white">{p.name}</h3>
                  <p className="text-xs text-surface-500 mt-0.5">{p.brand} · {p.category} · SKU {p.sku || '—'}</p>
                </div>
              </div>
              <span className="badge-neutral text-[10px]">Selected Product</span>
            </div>
          </div>
          <div className="card-body py-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">PricePilot Price</p>
                <p className="text-xl font-bold text-surface-900 dark:text-white mt-1">{fmt(p.current_price)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Stock</p>
                <p className="text-xl font-bold text-surface-900 dark:text-white mt-1">{p.stock_quantity ?? '—'}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Model</p>
                <p className="text-lg font-semibold text-surface-900 dark:text-white mt-1">{p.model || '—'}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Specs</p>
                <div className="mt-1"><Specs specs={p.parsed_specs} /></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Market Position Summary ── */}
      {p && !loading && allCompetitors.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="card p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Lowest</p>
            <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">{fmt(marketLow)}</p>
          </div>
          <div className="card p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Average</p>
            <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">{fmt(marketAvg)}</p>
          </div>
          <div className="card p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Highest</p>
            <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">{fmt(marketHigh)}</p>
          </div>
          <div className="card p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-400 font-medium">Position</p>
            {marketLow != null && ourPrice ? (
              <div className="mt-1">
                {ourPrice < marketLow ? (
                  <span className="badge-success"><TrendingDown className="w-3 h-3" /> Below range</span>
                ) : ourPrice > marketHigh ? (
                  <span className="badge-danger"><TrendingUp className="w-3 h-3" /> Above range</span>
                ) : (
                  <span className="badge-info"><Minus className="w-3 h-3" /> Within range</span>
                )}
              </div>
            ) : <p className="text-lg font-bold text-surface-400 mt-1">—</p>}
          </div>
        </div>
      )}

      {/* ── Competitor Products Table ── */}
      {p && !loading && allCompetitors.length > 0 && (
        <div className="card overflow-hidden">
          <div className="card-header">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary-500" />
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Competitor Products</h3>
              <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-surface-100 dark:bg-surface-700 text-surface-500">{allCompetitors.length}</span>
            </div>
            <p className="text-[11px] text-surface-400 mt-1">Reference prices from PricePilot catalog — compare alongside verified live data where available.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-50 dark:bg-surface-800/50">
                  <th className="table-header text-left pl-5 w-[40%]">Competitor Product</th>
                  <th className="table-header text-right w-[15%]">Price</th>
                  <th className="table-header text-right w-[15%]">vs PricePilot</th>
                  <th className="table-header text-center w-[12%]">Match</th>
                  <th className="table-header text-left w-[18%]">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                {allCompetitors.map((c) => {
                  const srcs = c.marketplace_sources || c.platforms || [];
                  const price = c.price ?? c.reference_price;
                  const priceSrc = c.price_source || c.price_status;
                  return (
                    <tr key={c.product_id} className="table-row">
                      {/* Competitor Product */}
                      <td className="pl-5 py-3">
                        <p className="text-sm font-medium text-surface-900 dark:text-white leading-snug">{c.name}</p>
                        <p className="text-[11px] text-surface-400 mt-0.5">{c.brand} · {c.category}</p>
                        {c.parsed_specs && Object.keys(c.parsed_specs).length > 0 && (
                          <div className="mt-1.5"><Specs specs={c.parsed_specs} /></div>
                        )}
                      </td>
                      {/* Price */}
                      <td className="text-right py-3 pr-4">
                        <p className="font-mono font-semibold text-sm text-surface-900 dark:text-white">{fmt(price)}</p>
                        <div className="mt-0.5 flex justify-end"><PriceBadge status={priceSrc} /></div>
                      </td>
                      {/* Difference */}
                      <td className="text-right py-3">
                        <Diff pct={c.price_difference_pct} />
                        <p className="text-[10px] text-surface-400 mt-0.5 font-mono">
                          {c.price_difference >= 0 ? '+' : ''}{fmt(c.price_difference)}
                        </p>
                      </td>
                      {/* Match */}
                      <td className="text-center py-3">
                        <MatchBadge matchType={c.match_type} />
                        <p className="text-[10px] text-surface-400 mt-0.5">{(c.similarity_score ?? 0).toFixed(0)}% match</p>
                      </td>
                      {/* Source */}
                      <td className="py-3">
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

      {/* ── Empty State ── */}
      {p && !loading && allCompetitors.length === 0 && (
        <div className="card">
          <div className="card-body text-center py-12">
            <div className="p-3 rounded-xl bg-surface-100 dark:bg-surface-800 inline-flex mb-4">
              <Layers className="w-7 h-7 text-surface-400" />
            </div>
            <p className="text-sm font-medium text-surface-900 dark:text-white">No comparable products found</p>
            <p className="text-xs text-surface-500 mt-1.5 max-w-xs mx-auto leading-relaxed">
              No same-category products within the price band matched the brand, specifications or product type.
            </p>
          </div>
        </div>
      )}

      {/* ── Marketplace Sources (collapsible) ── */}
      {p && !loading && sources.length > 0 && (
        <details className="group">
          <summary className="flex items-center gap-2 cursor-pointer text-[11px] text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 transition-colors select-none">
            <Globe className="w-3.5 h-3.5" />
            <span>{sources.length} marketplace sources for "{p.name}"</span>
            <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
          </summary>
          <div className="mt-2 p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50">
            <p className="text-[11px] text-surface-400 mb-2">Open to verify the current market price — sources, not competitors.</p>
            <SourceLinks sources={sources} />
          </div>
        </details>
      )}

      {/* ── Data Note (compact) ── */}
      {data && !loading && (
        <details className="group">
          <summary className="flex items-center gap-2 cursor-pointer text-[11px] text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 transition-colors select-none">
            <Info className="w-3.5 h-3.5" />
            <span>Data methodology</span>
            <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
          </summary>
          <div className="mt-2 p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50 text-[11px] text-surface-500 dark:text-surface-400 leading-relaxed">
            <strong>Competitors</strong> are other products (exact or closely matching) — not marketplaces.{' '}
            <strong>Sources</strong> (Amazon India, Flipkart, Croma, etc.) are verification links only.{' '}
            Prices shown are PricePilot catalog reference prices. Live external prices are shown only when a permitted provider confirms them.
          </div>
        </details>
      )}

      {/* ── Market Intelligence & Pricing Report ── */}
      {selectedId && !loading && (
        <>
          <MarketIntelligence productId={selectedId} />
          <PricingComparisonReport productId={selectedId} />
        </>
      )}
    </div>
  );
}
