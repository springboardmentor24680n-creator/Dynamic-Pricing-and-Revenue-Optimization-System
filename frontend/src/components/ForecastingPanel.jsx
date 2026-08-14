import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { aiAPI, productsAPI } from '../api/client';
import { useToast } from '../context/ToastContext';
import {
  LineChart as LineChartIcon, TrendingUp, TrendingDown, Minus, Loader2,
  RefreshCw, CalendarRange, BarChart3, AlertCircle, Sparkles, ArrowRight,
  Activity, Sun, Snowflake, Flower2, Leaf, PartyPopper,
} from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, Legend, BarChart, Bar, Cell,
} from 'recharts';

const CHART_COLORS = { actual: '#2563eb', forecast: '#8b5cf6', band: '#8b5cf6' };

// Milestone 2 horizons: short (7/14/30d), medium (3M/6M), long (12M)
const HORIZONS = [
  { d: 7, l: '7D' }, { d: 14, l: '14D' }, { d: 30, l: '30D' },
  { d: 90, l: '3M' }, { d: 180, l: '6M' }, { d: 365, l: '12M' },
];

function formatMoney(v) {
  return `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

// Custom tooltip: only the meaningful series (Actual / Forecast / 80% bounds) are
// shown — the stacked band and boundary helper series are filtered out.
function ForecastTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  // Filter to the meaningful series and dedupe: the stacked band + dashed
  // boundary helpers can share dataKeys (e.g. cover Area and boundary Line
  // both use 'yhat_lower'), which would otherwise render duplicate rows.
  const seen = new Set();
  const series = payload.filter((p) => {
    if (!['actual', 'yhat', 'yhat_lower', 'yhat_upper'].includes(p.dataKey)) return false;
    if (seen.has(p.dataKey)) return false;
    seen.add(p.dataKey);
    return true;
  });
  if (!series.length) return null;
  const labels = { actual: 'Actual', yhat: 'Forecast', yhat_lower: 'Lower (80%)', yhat_upper: 'Upper (80%)' };
  return (
    <div className="rounded-xl border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-800 px-3.5 py-2.5 shadow-lg text-xs">
      <p className="font-semibold text-surface-900 dark:text-white mb-1.5">{label}</p>
      <div className="space-y-1">
        {series.map((s) => (
          <div key={s.dataKey} className="flex items-center justify-between gap-6">
            <span className="flex items-center gap-1.5 text-surface-500 dark:text-surface-400">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color || (s.dataKey === 'actual' ? CHART_COLORS.actual : CHART_COLORS.forecast) }} />
              {labels[s.dataKey] || s.dataKey}
            </span>
            <span className="font-mono font-medium text-surface-900 dark:text-white">{formatMoney(s.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TrendBadge({ trend, growth }) {
  if (trend === 'up') {
    return <span className="badge-success"><TrendingUp className="w-3 h-3" /> +{growth}%</span>;
  }
  if (trend === 'down') {
    return <span className="badge-danger"><TrendingDown className="w-3 h-3" /> {growth}%</span>;
  }
  if (trend === 'stable') {
    return <span className="badge-neutral"><Minus className="w-3 h-3" /> {growth}%</span>;
  }
  return <span className="badge-neutral">Unavailable</span>;
}

export default function ForecastingPanel({ onUseInOptimization }) {
  const toast = useToast();
  const [products, setProducts] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [horizon, setHorizon] = useState(30);
  const [forecast, setForecast] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingForecast, setLoadingForecast] = useState(false);
  // Guards against stale responses when the product/horizon changes quickly
  const requestSeq = useRef(0);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await productsAPI.list({ limit: 100 });
      const items = res.data.items || [];
      setProducts(items);
      if (items.length > 0) setSelectedId((prev) => prev || items[0].id);
    } catch (err) {
      toast.error('Failed to load products', err.response?.data?.detail);
    }
  }, [toast]);

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await aiAPI.forecastPortfolio(horizon);
      setPortfolio(res.data);
    } catch { /* portfolio is auxiliary */ } finally {
      setLoading(false);
    }
  }, [horizon]);

  const runForecast = useCallback(async (productId, h, forceRetrain) => {
    if (!productId) return;
    const seq = ++requestSeq.current;
    setLoadingForecast(true);
    try {
      const res = await aiAPI.forecast(productId, h, forceRetrain);
      if (seq !== requestSeq.current) return; // a newer request superseded this one
      setForecast(res.data);
    } catch (err) {
      if (seq !== requestSeq.current) return;
      toast.error('Forecast failed', err.response?.data?.detail);
      setForecast(null);
    } finally {
      if (seq === requestSeq.current) setLoadingForecast(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  // Auto-run forecast whenever the selected product or horizon changes
  useEffect(() => {
    if (selectedId) runForecast(selectedId, horizon, false);
  }, [selectedId, horizon, runForecast]);

  const handleRetrain = () => {
    if (!selectedId) return;
    runForecast(selectedId, horizon, true);
    toast.info('Retraining Prophet model', 'Fresh forecast requested — this can take a few seconds');
  };

  const handleUseInOptimization = () => {
    if (!selectedId || !forecast?.points?.length) {
      toast.error('Forecast unavailable', 'Run a forecast for this product first');
      return;
    }
    const product = products.find((p) => p.id === selectedId);
    if (product && onUseInOptimization) {
      onUseInOptimization(product, forecast);
    }
  };

  // Prophet decomposition window: components cover history + forecast; slice a
  // ~90-day window centred on today so the weekly wave stays readable.
  const components = forecast?.components || [];
  const compWindow = useMemo(() => {
    if (!components.length) return [];
    const hLen = forecast?.history?.length || 0;
    const start = Math.max(0, hLen - 45);
    const end = Math.min(components.length, hLen + 45);
    return components.slice(start, end);
  }, [components, forecast?.history?.length]);

  // Merge history + forecast into a single chart series (keep last 45 history days)
  const chartData = useMemo(() => {
    const merged = [];
    const history = forecast?.history || [];
    const recent = history.slice(-45);
    recent.forEach((h) => merged.push({ date: h.date, actual: h.actual }));
    (forecast?.points || []).forEach((p) =>
      merged.push({
        date: p.date,
        yhat: p.yhat,
        yhat_lower: p.yhat_lower,
        yhat_upper: p.yhat_upper,
        band: p.yhat_upper - p.yhat_lower, // band height for the stacked confidence area
      })
    );
    return merged;
  }, [forecast]);

  const metrics = forecast?.metrics || {};
  const avgBandWidth = useMemo(() => {
    const pts = forecast?.points || [];
    if (!pts.length) return 0;
    return pts.reduce((acc, p) => acc + (p.yhat_upper - p.yhat_lower) / Math.max(p.yhat, 1), 0) / pts.length * 100;
  }, [forecast]);

  const fmtUnits = (v) =>
    v == null ? '—' : Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });

  const kpis = [
    {
      label: 'Forecast Revenue',
      value: formatMoney(metrics.forecast_revenue_total),
      sub: `next ${horizon} days`,
      icon: BarChart3, color: 'text-violet-600 dark:text-violet-400', bg: 'bg-violet-100 dark:bg-violet-900/30',
    },
    {
      label: 'Growth vs Trailing',
      value: `${metrics.growth_pct ?? 0}%`,
      sub: metrics.source === 'prophet' ? 'Prophet model' : 'Trend estimate',
      icon: TrendingUp, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/30',
    },
    {
      label: 'Avg Daily Revenue',
      value: formatMoney(metrics.avg_daily_revenue),
      sub: `last actual ${formatMoney(metrics.last_actual)}`,
      icon: Activity, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    },
    {
      label: '80% CI Width',
      value: `±${avgBandWidth.toFixed(0)}%`,
      sub: 'avg prediction interval',
      icon: CalendarRange, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30',
    },
  ];

  const selectedProduct = products.find((p) => p.id === selectedId);
  const insufficient = forecast?.insufficient_data;
  const isFallback = forecast?.fallback;
  const da = forecast?.demand_analysis || {};
  const seasonality = forecast?.seasonality || {};

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex-1 min-w-[240px]">
              <label className="label">Product</label>
              <select
                className="input"
                value={selectedId}
                onChange={(e) => setSelectedId(Number(e.target.value))}
                disabled={loadingForecast}
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Forecast Horizon</label>
              <div className="flex items-center gap-1 p-1 rounded-lg bg-surface-100 dark:bg-surface-700/60">
                {HORIZONS.map(({ d, l }) => (
                  <button
                    key={d}
                    onClick={() => setHorizon(d)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      horizon === d
                        ? 'bg-white dark:bg-surface-600 text-primary-600 dark:text-primary-300 shadow-sm'
                        : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-200'
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => runForecast(selectedId, horizon, false)} disabled={loadingForecast} className="btn-primary">
                {loadingForecast ? <Loader2 className="w-4 h-4 animate-spin" /> : <LineChartIcon className="w-4 h-4" />}
                Run Forecast
              </button>
              <button onClick={handleRetrain} disabled={loadingForecast} className="btn-secondary btn-sm" title="Force Prophet retrain (ignore cache)">
                <RefreshCw className={`w-3.5 h-3.5 ${loadingForecast ? 'animate-spin' : ''}`} />
                Retrain
              </button>
            </div>
          </div>
          {isFallback && (
            <p className="mt-3 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              {forecast?.fallback_reason === 'prophet_unavailable'
                ? 'Prophet STAN backend is unavailable in this environment — showing a fast trend estimate with confidence bounds instead.'
                : 'Limited sales history — showing a fast trend estimate instead of a full Prophet fit.'}
            </p>
          )}
          {forecast?.horizon_note && (
            <p className="mt-3 text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              {forecast.horizon_note}
            </p>
          )}
        </div>
      </div>

      {insufficient ? (
        <div className="card">
          <div className="card-body">
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-amber-700 dark:text-amber-300">{forecast?.recommendation}</p>
            </div>
          </div>
        </div>
      ) : forecast ? (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {kpis.map((k) => {
              const Icon = k.icon;
              return (
                <div key={k.label} className="stat-card">
                  <div className="flex items-center justify-between">
                    <span className="stat-label">{k.label}</span>
                    <div className={`p-2 rounded-lg ${k.bg}`}>
                      <Icon className={`w-4 h-4 ${k.color}`} />
                    </div>
                  </div>
                  <span className="stat-value">{k.value}</span>
                  <span className="stat-description">{k.sub}</span>
                </div>
              );
            })}
          </div>

          {/* Demand trend banner */}
          <div className="card overflow-hidden border-l-4 border-l-violet-500">
            <div className="card-body flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-violet-100 dark:bg-violet-900/30">
                  <TrendingUp className="w-6 h-6 text-violet-600 dark:text-violet-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-surface-900 dark:text-white">Demand Signal — {selectedProduct?.name}</p>
                  <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
                    {metrics.source === 'prophet' ? 'Prophet model' : 'Linear trend'} · trained on {forecast.history?.length} days of sales history
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 lg:ml-auto">
                <TrendBadge trend={metrics.trend} growth={metrics.growth_pct} />
                <button onClick={handleUseInOptimization} className="btn-primary btn-sm">
                  <Sparkles className="w-3.5 h-3.5" /> Use in Optimization
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Compact Demand Analysis (Milestone 2) */}
          {da?.available && (
            <div className="card overflow-hidden border-l-4 border-l-blue-500">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-500" /> Demand Analysis
                  </h3>
                  <span className="text-xs text-surface-400">historical vs forecast demand · {horizon}d</span>
                </div>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                  <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">Historical Demand</p>
                    <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">{fmtUnits(da.historical_units)}</p>
                    <p className="text-[10px] text-surface-400 mt-0.5">{da.historical_days} days · {fmtUnits(da.avg_daily_units)}/day</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">Forecast Demand</p>
                    <p className="text-lg font-bold text-blue-600 dark:text-blue-400 mt-1">{fmtUnits(da.forecast_units)}</p>
                    <p className="text-[10px] text-surface-400 mt-0.5">next {horizon} days</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">Demand Change</p>
                    <div className="mt-1">
                      <TrendBadge trend={da.trend} growth={da.demand_change_pct} />
                    </div>
                    <p className="text-[10px] text-surface-400 mt-1">vs trailing {Math.min(horizon, da.historical_days)} days</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">Forecast Confidence</p>
                    <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">
                      {metrics.forecast_confidence != null ? `${metrics.forecast_confidence.toFixed(0)}%` : '—'}
                    </p>
                    <p className="text-[10px] text-surface-400 mt-0.5">from 80% CI band</p>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">Avg Unit Price</p>
                    <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">{formatMoney(da.avg_unit_price)}</p>
                    <p className="text-[10px] text-surface-400 mt-0.5">realized in history</p>
                  </div>
                </div>
                {da.insight && (
                  <p className="mt-4 text-sm text-surface-600 dark:text-surface-300 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/50 rounded-xl p-3">
                    {da.insight}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Seasonal Trend Analysis (Milestone 2) */}
          {seasonality?.supported && (
            <div className="card">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-violet-500" /> Seasonal Trend Analysis
                  </h3>
                  <span className="text-xs text-surface-400">weekly & monthly patterns from real sales history</span>
                </div>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <p className="text-[11px] font-medium text-surface-500 mb-2">Day of Week — demand index vs weekly average</p>
                    <ResponsiveContainer width="100%" height={190}>
                      <BarChart data={seasonality.day_of_week || []} margin={{ top: 5, right: 5, left: -18, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
                        <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                        <Tooltip cursor={{ fill: '#f1f5f9' }} contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                        <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                        <Bar dataKey="index" radius={[4, 4, 0, 0]}>
                          {(seasonality.day_of_week || []).map((d) => (
                            <Cell key={d.day} fill={d.index >= 1.15 ? '#7c3aed' : d.index <= 0.85 ? '#f59e0b' : '#c4b5fd'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <p className="text-[11px] font-medium text-surface-500 mb-2">Month — demand index vs overall average</p>
                    {seasonality.monthly?.length ? (
                      <ResponsiveContainer width="100%" height={190}>
                        <BarChart data={seasonality.monthly} margin={{ top: 5, right: 5, left: -18, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
                          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
                          <Tooltip cursor={{ fill: '#f1f5f9' }} contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                          <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" />
                          <Bar dataKey="index" radius={[4, 4, 0, 0]}>
                            {seasonality.monthly.map((m) => (
                              <Cell key={m.month} fill={m.index >= 1.15 ? '#7c3aed' : m.index <= 0.85 ? '#f59e0b' : '#c4b5fd'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[190px] flex items-center justify-center rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-dashed border-surface-200 dark:border-surface-700">
                        <p className="text-sm text-surface-400 px-6 text-center">
                          Not enough history to identify a reliable monthly pattern (need ~1.5 months of sales).
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                {seasonality.insight_text && (
                  <p className="mt-4 text-sm text-surface-600 dark:text-surface-300 bg-violet-50 dark:bg-violet-900/20 border border-violet-100 dark:border-violet-800/50 rounded-xl p-3">
                    {seasonality.insight_text}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Business Seasonality — real seasonal & festival demand insights */}
          {forecast?.business_seasonality?.supported && (
            <div className="card">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                    <Sun className="w-4 h-4 text-amber-500" /> Business Seasonality Analysis
                  </h3>
                  <span className="text-xs text-surface-400">real seasonal & festival demand from sales history</span>
                </div>
              </div>
              <div className="card-body">
                {/* Season cards: Winter / Spring / Summer / Autumn */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {(forecast.business_seasonality.seasons || []).map((s) => {
                    const SeasonIcon = s.season === 'Winter' ? Snowflake
                      : s.season === 'Spring' ? Flower2
                      : s.season === 'Summer' ? Sun : Leaf;
                    return (
                      <div key={s.season} className={`p-3.5 rounded-xl border ${
                        !s.supported
                          ? 'border-amber-200 dark:border-amber-800 bg-amber-50/60 dark:bg-amber-900/10'
                          : s.direction === 'higher'
                            ? 'border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/60 dark:bg-emerald-900/10'
                            : s.direction === 'lower'
                              ? 'border-sky-200 dark:border-sky-800/60 bg-sky-50/60 dark:bg-sky-900/10'
                              : 'border-surface-200 dark:border-surface-700 bg-surface-50/60 dark:bg-surface-800/40'
                      }`}>
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <SeasonIcon className="w-4 h-4 text-amber-500" />
                            <span className="text-sm font-semibold text-surface-900 dark:text-white">{s.season}</span>
                          </div>
                          {!s.supported ? (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400">
                              Insufficient
                            </span>
                          ) : s.direction === 'higher' ? (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400">
                              {s.change_pct >= 0 ? '+' : ''}{s.change_pct}%
                            </span>
                          ) : s.direction === 'lower' ? (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-sky-100 dark:bg-sky-900/40 text-sky-700 dark:text-sky-400">
                              {s.change_pct >= 0 ? '+' : ''}{s.change_pct}%
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-surface-100 dark:bg-surface-700/60 text-surface-500 dark:text-surface-400">
                              {s.change_pct >= 0 ? '+' : ''}{s.change_pct}%
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-surface-500 dark:text-surface-400 mb-2">
                          {s.months} · {s.days_covered} days covered
                          {s.supported && (
                            <span className="block text-surface-400">
                              {s.avg_daily_units} vs {s.year_avg_daily_units} units/day
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-surface-600 dark:text-surface-300 leading-snug">
                          {s.insight}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* Festival / holiday impact */}
                <div className={`mt-3 p-3.5 rounded-xl border ${
                  forecast.business_seasonality.festival?.supported
                    ? 'border-violet-200 dark:border-violet-800/60 bg-violet-50/60 dark:bg-violet-900/10'
                    : 'border-amber-200 dark:border-amber-800 bg-amber-50/60 dark:bg-amber-900/10'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <PartyPopper className="w-4 h-4 text-violet-500" />
                    <span className="text-sm font-semibold text-surface-900 dark:text-white">Festival / Holiday Periods</span>
                  </div>
                  {forecast.business_seasonality.festival?.supported ? (
                    <>
                      <p className="text-xs text-surface-600 dark:text-surface-300">
                        {forecast.business_seasonality.festival.insight}
                      </p>
                      <p className="mt-1 text-[11px] text-surface-400">
                        {forecast.business_seasonality.festival.avg_festival_units} units/day on festival days vs{' '}
                        {forecast.business_seasonality.festival.avg_normal_units} units/day normally
                        {forecast.business_seasonality.festival.baseline_note && ` (${forecast.business_seasonality.festival.baseline_note})`}
                      </p>
                    </>
                  ) : (
                    <p className="text-xs text-amber-600 dark:text-amber-400">
                      {forecast.business_seasonality.festival?.insight}
                    </p>
                  )}
                </div>

                {/* Concise insight list */}
                {forecast.business_seasonality.insights?.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {forecast.business_seasonality.insights.map((ins, i) => (
                      <p key={i} className="flex items-start gap-2 text-xs text-surface-600 dark:text-surface-300">
                        <Sparkles className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                        {ins}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Model Inputs — data coverage (Milestone 2) */}
          {forecast?.data_coverage && (
            <div className="card">
              <div className="card-header">
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary-500" /> Model Inputs — Data Coverage
                </h3>
              </div>
              <div className="card-body">
                <p className="text-[11px] font-medium text-surface-500 mb-2">Available in current dataset</p>
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {forecast.data_coverage.available.map((f) => (
                    <span key={f} className="px-2 py-1 rounded-md bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-medium">
                      {f}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] font-medium text-amber-600 dark:text-amber-400 mb-2">Not available in current dataset</p>
                <div className="flex flex-wrap gap-1.5">
                  {forecast.data_coverage.unavailable.map((f) => (
                    <span key={f} className="px-2 py-1 rounded-md bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-[10px] font-medium">
                      {f}
                    </span>
                  ))}
                </div>
                <p className="mt-3 text-[11px] text-surface-400">{forecast.data_coverage.note}</p>
              </div>
            </div>
          )}

          {/* Confidence band chart */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
                  Revenue Forecast — {horizon}-Day Horizon
                </h3>
                <span className="text-xs text-surface-400">80% confidence interval</span>
              </div>
            </div>
            <div className="card-body">
              {chartData.length === 0 ? (
                <div className="empty-state py-12">
                  <AlertCircle className="w-10 h-10 text-surface-300 dark:text-surface-600 mb-3" />
                  <p className="text-sm text-surface-500 dark:text-surface-400">No forecast points generated</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v?.slice(5)} minTickGap={24} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}`} />
                    <Tooltip content={<ForecastTooltip />} cursor={{ stroke: '#94a3b8', strokeDasharray: '4 4' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <ReferenceLine
                      x={forecast?.history?.length ? forecast.history[forecast.history.length - 1]?.date : undefined}
                      stroke="#94a3b8"
                      strokeDasharray="4 4"
                      label={{ value: 'Today', fontSize: 10, fill: '#94a3b8', position: 'insideTopRight' }}
                    />
                    {/* Stacked band: lower bound (cover) + band height = upper bound, so the
                        shaded region renders exactly between the two bounds. */}
                    <Area dataKey="yhat_lower" stackId="band" stroke="none" className="forecast-cover" legendType="none" />
                    <Area dataKey="band" stackId="band" stroke="none" fill="url(#forecastBand)" legendType="none" />
                    <Line type="monotone" dataKey="yhat_lower" stroke={CHART_COLORS.forecast} strokeWidth={1} strokeDasharray="4 4" strokeOpacity={0.5} dot={false} legendType="none" />
                    <Line type="monotone" dataKey="yhat_upper" stroke={CHART_COLORS.forecast} strokeWidth={1} strokeDasharray="4 4" strokeOpacity={0.5} dot={false} legendType="none" />
                    <Line type="monotone" dataKey="yhat" name="Forecast" stroke={CHART_COLORS.forecast} strokeWidth={2.5} dot={false} />
                    <Line type="monotone" dataKey="actual" name="Actual" stroke={CHART_COLORS.actual} strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Prophet Decomposition — real fitted components */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-blue-500" /> Prophet Decomposition
                </h3>
                <span className="text-xs text-surface-400">fitted trend + weekly seasonality</span>
              </div>
            </div>
            <div className="card-body">
              {components.length === 0 ? (
                <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                  <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    Decomposition is available when the Prophet model fits. This forecast used the fast trend
                    estimate (fallback), so the fitted trend and weekly-seasonality components are not available
                    for this run.
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div>
                      <p className="text-[11px] font-medium text-surface-500 mb-2">Trend Component — long-run revenue level ($)</p>
                      <ResponsiveContainer width="100%" height={200}>
                        <ComposedChart data={compWindow} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                          <defs>
                            <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
                          <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v?.slice(5)} minTickGap={28} />
                          <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${Number(v).toLocaleString()}`} />
                          <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} formatter={(v) => `$${Number(v).toLocaleString()}`} />
                          <Area type="monotone" dataKey="trend" stroke="#2563eb" strokeWidth={2} fill="url(#trendGrad)" name="Trend" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-surface-500 mb-2">Weekly Seasonality — repeating 7-day effect ($)</p>
                      <ResponsiveContainer width="100%" height={200}>
                        <ComposedChart data={compWindow} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.5} />
                          <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v?.slice(5)} minTickGap={28} />
                          <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${Number(v).toLocaleString()}`} />
                          <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} formatter={(v) => `$${Number(v).toLocaleString()}`} />
                          <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
                          <Line type="monotone" dataKey="weekly" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Weekly" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  <p className="mt-3 text-[11px] text-surface-400">
                    Components read directly from the fitted Prophet model — the trend is the long-run revenue
                    level and weekly is the repeating 7-day effect around it (real fitted values, never synthetic).
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Forecast table */}
          <div className="card overflow-hidden">
            <div className="card-header">
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Forecast Points</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-50 dark:bg-surface-800/50">
                    <th className="table-header">Date</th>
                    <th className="table-header text-right">Forecast</th>
                    <th className="table-header text-right">Lower (80%)</th>
                    <th className="table-header text-right">Upper (80%)</th>
                    <th className="table-header text-right">Range</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                  {(forecast?.points || []).map((p) => (
                    <tr key={p.date} className="table-row">
                      <td className="table-cell font-mono text-xs">{p.date}</td>
                      <td className="table-cell text-right font-mono font-semibold text-violet-600 dark:text-violet-400">
                        {formatMoney(p.yhat)}
                      </td>
                      <td className="table-cell text-right font-mono">{formatMoney(p.yhat_lower)}</td>
                      <td className="table-cell text-right font-mono">{formatMoney(p.yhat_upper)}</td>
                      <td className="table-cell text-right">
                        <span className="text-xs text-surface-500">
                          {formatMoney(p.yhat_upper - p.yhat_lower)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <div className="card-body flex items-center justify-center py-16">
            {loading ? (
              <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
            ) : (
              <div className="empty-state">
                <LineChartIcon className="w-12 h-12 text-surface-300 dark:text-surface-600 mb-3" />
                <p className="text-sm text-surface-500 dark:text-surface-400">Select a product and run a forecast</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Portfolio outlook */}
      {portfolio && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <div className="card-header">
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-500" /> Top Growing Demand
              </h3>
            </div>
            <div className="card-body space-y-3">
              {portfolio.top_growing?.length === 0 ? (
                <p className="text-sm text-surface-400">No products with rising demand right now.</p>
              ) : (
                portfolio.top_growing?.map((r) => (
                  <div key={r.product_id} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-surface-900 dark:text-white truncate">{r.product_name}</p>
                      <p className="text-xs text-surface-400">{r.category}</p>
                    </div>
                    <TrendBadge trend="up" growth={r.growth_pct} />
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-red-500" /> Softening Demand
              </h3>
            </div>
            <div className="card-body space-y-3">
              {portfolio.top_declining?.length === 0 ? (
                <p className="text-sm text-surface-400">No products with declining demand right now.</p>
              ) : (
                portfolio.top_declining?.map((r) => (
                  <div key={r.product_id} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-surface-900 dark:text-white truncate">{r.product_name}</p>
                      <p className="text-xs text-surface-400">{r.category}</p>
                    </div>
                    <TrendBadge trend="down" growth={r.growth_pct} />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
