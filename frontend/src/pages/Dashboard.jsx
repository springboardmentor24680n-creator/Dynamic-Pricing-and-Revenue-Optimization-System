import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  dashboardAPI, activityAPI, aiAPI, salesAPI, pricingAPI, productsAPI, datasetsAPI,
} from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import usePendingRequests from '../hooks/usePendingRequests';
import {
  Package, TrendingUp, DollarSign, Database, Activity, ArrowRight, RefreshCw,
  Loader2, AlertCircle, BrainCircuit, FileSpreadsheet, Boxes, UserCheck, Clock,
  Sparkles, Target, TrendingDown, Gauge, ShieldCheck, CheckCircle2, UploadCloud,
  LineChart as LineChartIcon, FileDown, Crown, LogIn, UserPlus,
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const fmtMoney = (v) => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtMoney2 = (v) => `$${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const LOW_CONFIDENCE_THRESHOLD = 70;

function computeGrowth(trend) {
  if (!trend || trend.length < 2) return null;
  const vals = trend.map((p) => Number(p.revenue) || 0);
  const split = Math.max(1, Math.floor(vals.length * 0.6));
  const recent = vals.slice(split).reduce((a, b) => a + b, 0);
  const prior = vals.slice(0, split).reduce((a, b) => a + b, 0);
  if (prior === 0) return null;
  return ((recent - prior) / prior) * 100;
}

function activityMeta(action = '') {
  const a = action.toLowerCase();
  if (a.includes('dataset') || a.includes('import') || a.includes('upload'))
    return { icon: FileSpreadsheet, tint: 'bg-sky-100 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400' };
  if (a.includes('model') || a.includes('train') || a.includes('forecast') || a.includes('prediction') || a.includes('prophet'))
    return { icon: BrainCircuit, tint: 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400' };
  if (a.includes('price') || a.includes('recommendation') || a.includes('approv') || a.includes('reject'))
    return { icon: TrendingUp, tint: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' };
  if (a.includes('login'))
    return { icon: LogIn, tint: 'bg-surface-200 dark:bg-surface-700 text-surface-600 dark:text-surface-300' };
  if (a.includes('user') || a.includes('role') || a.includes('account'))
    return { icon: UserPlus, tint: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' };
  if (a.includes('product'))
    return { icon: Package, tint: 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400' };
  return { icon: Activity, tint: 'bg-surface-200 dark:bg-surface-700 text-surface-600 dark:text-surface-300' };
}

const statusBadge = (status) => {
  switch (status) {
    case 'Optimal': return <span className="badge-success"><CheckCircle2 className="w-3 h-3 mr-1" />Optimal</span>;
    case 'Needs Increase': return <span className="badge-info"><TrendingUp className="w-3 h-3 mr-1" />Needs Increase</span>;
    case 'Needs Decrease': return <span className="badge-warning"><TrendingDown className="w-3 h-3 mr-1" />Needs Decrease</span>;
    case 'Review Required': return <span className="badge-danger"><AlertCircle className="w-3 h-3 mr-1" />Review Required</span>;
    default: return <span className="badge-neutral">Not Analyzed</span>;
  }
};

/* ------------------------------------------------------------------ */
/* Skeleton                                                            */
/* ------------------------------------------------------------------ */

function SkeletonCards() {
  return (
    <div className="page-transition space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card p-6">
            <div className="skeleton h-4 w-24 mb-3"></div>
            <div className="skeleton h-8 w-20"></div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2 h-80"><div className="skeleton h-full w-full rounded-xl"></div></div>
        <div className="card h-80"><div className="skeleton h-full w-full rounded-xl"></div></div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2 h-64"><div className="skeleton h-full w-full rounded-xl"></div></div>
        <div className="card h-64"><div className="skeleton h-full w-full rounded-xl"></div></div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Empty state                                                         */
/* ------------------------------------------------------------------ */

function EmptyState({ icon: Icon, title, hint, cta }) {
  return (
    <div className="empty-state py-12">
      <div className="p-3 rounded-xl bg-surface-100 dark:bg-surface-700/50 mb-3">
        <Icon className="w-7 h-7 text-surface-400 dark:text-surface-500" />
      </div>
      <p className="text-sm font-medium text-surface-700 dark:text-surface-300">{title}</p>
      {hint && <p className="text-xs text-surface-400 dark:text-surface-500 mt-1 max-w-xs">{hint}</p>}
      {cta && (
        <Link to={cta.to} className="text-xs text-primary-600 dark:text-primary-400 font-medium mt-3 hover:underline">
          {cta.label}
        </Link>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Dashboard                                                      */
/* ------------------------------------------------------------------ */

export default function Dashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const { count: pendingRequests } = usePendingRequests();

  const [data, setData] = useState(null);
  const [activity, setActivity] = useState([]);
  const [aiStatus, setAiStatus] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [allProducts, setAllProducts] = useState([]); // full catalog (up to 100) for revenue mapping
  const [topProducts, setTopProducts] = useState([]); // top 5 displayed
  const [latestDataset, setLatestDataset] = useState(null);
  const [trend, setTrend] = useState([]);
  const [range, setRange] = useState(30);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [approving, setApproving] = useState(null);

  const fallbackTrendRef = useRef([]); // last dashboard 14-day series, used if sales API is empty

  const isAdminOrPricing = user?.role === 'admin' || user?.role === 'pricing_manager';

  const loadTrend = useCallback(async (days) => {
    try {
      const res = await salesAPI.analytics(days);
      const daily = Array.isArray(res.data?.daily_revenue) ? res.data.daily_revenue : [];
      if (daily.length) {
        setTrend(daily);
        return;
      }
    } catch { /* fall through to fallback */ }
    setTrend(fallbackTrendRef.current);
  }, []);

  const fetchAll = useCallback(async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const [dashRes, activityRes, aiRes, productsRes, recsRes, datasetsRes] = await Promise.all([
        dashboardAPI.getDashboard(),
        activityAPI.getLogs({ limit: 10 }).catch(() => ({ data: [] })),
        aiAPI.getStatus().catch(() => null),
        productsAPI.list({ sort_by: 'revenue', sort_order: 'desc', limit: 100 }).catch(() => ({ data: { items: [] } })),
        pricingAPI.listRecommendations({ limit: 50 }).catch(() => []),
        datasetsAPI.list({ limit: 1 }).catch(() => ({ data: { datasets: [] } })),
      ]);

      const dash = dashRes.data;
      setData(dash);
      setActivity(Array.isArray(activityRes.data) ? activityRes.data : []);
      setAiStatus(aiRes?.data || null);
      const items = productsRes.data?.items || [];
      setAllProducts(items);
      setTopProducts(items.slice(0, 5));
      const recs = Array.isArray(recsRes) ? recsRes : (Array.isArray(recsRes?.data) ? recsRes.data : []);
      setRecommendations(recs);
      setLatestDataset(datasetsRes.data?.datasets?.[0] || null);

      fallbackTrendRef.current = dash?.revenue_trend || [];
      await loadTrend(range);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [range, loadTrend]);

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-refresh after dataset imports / AI training / price changes.
  useEffect(() => {
    const id = setInterval(() => fetchAll(true), 90000);
    return () => clearInterval(id);
  }, [fetchAll]);

  /* ---------------- Derived analytics ---------------- */
  // NOTE: all useMemo/useCallback hooks must run BEFORE any early return
  // (the SkeletonCards guard below) to satisfy the Rules of Hooks.

  const pendingRecs = useMemo(() => recommendations.filter((r) => r.status === 'pending'), [recommendations]);

  // Revenue lookup across the whole fetched catalog so the revenue-opportunity
  // metric covers every product with a pending recommendation, not just the top 5.
  const productMap = useMemo(() => {
    const m = {};
    allProducts.forEach((p) => { m[p.id] = p; });
    return m;
  }, [allProducts]);

  // AI status per product, derived from real recommendations.
  const recStatusByProduct = useMemo(() => {
    const m = {};
    recommendations.forEach((r) => {
      const isIncrease = r.recommended_price > r.current_price;
      const isDecrease = r.recommended_price < r.current_price;
      let status = 'Not Analyzed';
      if (r.status === 'pending') status = isIncrease ? 'Needs Increase' : (isDecrease ? 'Needs Decrease' : 'Review Required');
      else if (r.status === 'applied') status = 'Optimal';
      else if (r.status === 'rejected') status = 'Review Required';
      m[r.product_id] = status;
    });
    return m;
  }, [recommendations]);

  const topRows = useMemo(() => topProducts.map((p, i) => {
    const margin = (p.current_price > 0 && p.cost_price != null)
      ? ((p.current_price - p.cost_price) / p.current_price) * 100
      : null;
    return {
      rank: i + 1,
      id: p.id,
      name: p.name,
      category: p.category || 'Uncategorized',
      price: p.current_price,
      revenue: p.revenue || 0,
      margin,
      status: recStatusByProduct[p.id] || 'Not Analyzed',
    };
  }), [topProducts, recStatusByProduct]);

  const underpriced = useMemo(
    () => pendingRecs.filter((r) => r.recommended_price > r.current_price),
    [pendingRecs],
  );
  const overpriced = useMemo(
    () => pendingRecs.filter((r) => r.recommended_price < r.current_price),
    [pendingRecs],
  );
  const lowConfidence = useMemo(
    () => pendingRecs.filter((r) => (r.confidence_score ?? 0) < LOW_CONFIDENCE_THRESHOLD),
    [pendingRecs],
  );

  const revenueOpportunity = useMemo(() => {
    return underpriced.reduce((sum, r) => {
      const upliftPct = ((r.recommended_price - r.current_price) / r.current_price) * 100;
      const product = productMap[r.product_id];
      const baseRevenue = product?.revenue ?? 0;
      return sum + (baseRevenue * upliftPct) / 100;
    }, 0);
  }, [underpriced, productMap]);

  const avgUplift = useMemo(() => {
    if (!pendingRecs.length) return null;
    const total = pendingRecs.reduce((s, r) => s + Math.abs(((r.recommended_price - r.current_price) / r.current_price) * 100), 0);
    return total / pendingRecs.length;
  }, [pendingRecs]);

  const growth = computeGrowth(trend);
  const aiReady = aiStatus?.status === 'ready';

  // Model performance from the persisted training run (model_info from backend).
  // Each candidate model carries real MAE / RMSE / R² measured at training time.
  const modelRows = useMemo(() => {
    const metrics = aiStatus?.model_info?.metrics || {};
    const names = Object.keys(metrics);
    if (!names.length) return [];
    const best = Math.max(...names.map((n) => metrics[n]?.r2 ?? -Infinity));
    return names.map((name) => ({
      name,
      mae: metrics[name]?.mae ?? 0,
      rmse: metrics[name]?.rmse ?? 0,
      r2: metrics[name]?.r2 ?? 0,
      // Relative performance: higher R² = better. Scale against best model.
      score: best > 0 ? Math.round((Math.max(metrics[name]?.r2 ?? 0, 0) / best) * 100) : 0,
      isBest: aiStatus?.best_model === name || metrics[name]?.r2 === best,
    }));
  }, [aiStatus]);

  if (loading && !data) return <SkeletonCards />;

  const kpis = [
    {
      label: 'Total Revenue', value: fmtMoney(data?.total_revenue ?? 0), icon: DollarSign,
      accent: 'text-emerald-500', bg: 'bg-emerald-100 dark:bg-emerald-900/30',
      desc: `${data?.revenue_summary?.margin ?? 0}% margin · avg ${fmtMoney2(data?.revenue_summary?.average_price ?? 0)}`,
    },
    {
      label: 'Total Products', value: data?.total_products ?? 0, icon: Package,
      accent: 'text-primary-500', bg: 'bg-primary-100 dark:bg-primary-900/30',
      desc: `${data?.active_products ?? 0} active · ${data?.in_stock ?? 0} in stock`,
    },
    {
      label: 'Datasets Loaded', value: data?.total_datasets ?? 0, icon: Database,
      accent: 'text-sky-500', bg: 'bg-sky-100 dark:bg-sky-900/30',
      desc: data?.dataset_status || 'No dataset loaded',
    },
    {
      label: 'AI Engine', value: aiReady ? 'Ready' : 'Needs Data', icon: BrainCircuit,
      accent: aiReady ? 'text-emerald-500' : 'text-amber-500',
      bg: aiReady ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-amber-100 dark:bg-amber-900/30',
      desc: aiStatus ? `Trained on ${aiStatus.samples} records · ${aiStatus.best_model || 'no model yet'}` : 'Upload a dataset to begin AI analysis',
    },
  ];

  const quickActions = [
    { to: '/datasets', icon: UploadCloud, label: 'Upload Dataset', desc: 'Import and process CSV / Excel' },
    { to: '/ai', icon: BrainCircuit, label: 'Run AI Prediction', desc: 'Optimize product prices' },
    { to: '/ai?tab=forecasting', icon: LineChartIcon, label: 'Generate Forecast', desc: 'Prophet demand forecasting' },
    { to: '/reports', icon: FileDown, label: 'Export Report', desc: 'PDF · Excel · CSV' },
    { to: '/products', icon: Package, label: 'Manage Products', desc: 'Catalog & inventory' },
  ];

  return (
    <div className="page-transition space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Pricing Intelligence Dashboard</h1>
          <p className="text-surface-500 dark:text-surface-400 mt-1">
            Welcome back, {user?.full_name || user?.username || 'User'} — real-time insights from your pricing engine
          </p>
        </div>
        <button onClick={() => fetchAll(true)} className="btn-secondary btn-sm">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Admin: pending access-request notification banner */}
      {user?.role === 'admin' && pendingRequests > 0 && (
        <div className="card !p-0 overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-gradient-to-r from-amber-50 to-transparent dark:from-amber-900/20 border-b border-amber-200 dark:border-amber-800">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex-shrink-0">
                <UserCheck className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-surface-900 dark:text-white">
                  {pendingRequests} pending access {pendingRequests === 1 ? 'request' : 'requests'}
                </p>
                <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Users are waiting for administrator approval before they can sign in.
                </p>
              </div>
            </div>
            <Link to="/access-requests" className="btn-primary btn-sm flex-shrink-0">
              <UserCheck className="w-4 h-4" />
              Review Requests
            </Link>
          </div>
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="stat-card">
              <div className="flex items-center justify-between">
                <span className="stat-label">{kpi.label}</span>
                <div className={`p-2 rounded-lg ${kpi.bg}`}>
                  <Icon className={`w-5 h-5 ${kpi.accent}`} />
                </div>
              </div>
              <span className="stat-value">{kpi.value}</span>
              <span className="stat-description">{kpi.desc}</span>
            </div>
          );
        })}
      </div>

      {/* Row 1: Revenue Trend + AI Pricing Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Trend */}
        <div className="card lg:col-span-2">
          <div className="card-header flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
                <TrendingUp className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Revenue Trend</h3>
                {growth !== null && (
                  <p className={`text-xs mt-0.5 flex items-center gap-1 font-medium ${growth >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                    {growth >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {growth >= 0 ? '+' : ''}{growth.toFixed(1)}% vs prior period
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1 p-1 rounded-lg bg-surface-100 dark:bg-surface-700/60 border border-surface-200 dark:border-surface-700">
              {[7, 30, 90].map((d) => (
                <button
                  key={d}
                  onClick={() => { setRange(d); loadTrend(d); }}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    range === d
                      ? 'bg-white dark:bg-surface-600 text-primary-600 dark:text-primary-300 shadow-sm'
                      : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-200'
                  }`}
                >
                  {d} Days
                </button>
              ))}
            </div>
          </div>
          <div className="card-body">
            {trend.length === 0 ? (
              <EmptyState
                icon={LineChartIcon}
                title="No sales data yet"
                hint="Upload a dataset with sales history to see the revenue trend here."
                cta={{ to: '/datasets', label: 'Go to Dataset Management' }}
              />
            ) : (
              <div>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={trend} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.15} vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: '#94a3b8' }}
                      tickFormatter={(v) => (range <= 30 ? v.slice(5) : v.slice(2))}
                      axisLine={false} tickLine={false} minTickGap={24}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#94a3b8' }}
                      tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}`}
                      axisLine={false} tickLine={false} width={52}
                    />
                    <Tooltip
                      formatter={(v) => [fmtMoney2(v), 'Revenue']}
                      labelFormatter={(l) => `Date: ${l}`}
                      contentStyle={{
                        borderRadius: 12, border: '1px solid rgba(100,116,139,0.25)',
                        background: '#1e293b', color: '#f1f5f9', fontSize: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
                      }}
                      labelStyle={{ color: '#94a3b8' }}
                    />
                    <Area
                      type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2.5}
                      fill="url(#revGrad)" activeDot={{ r: 5, strokeWidth: 2, stroke: '#0ea5e9' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* AI Pricing Insights */}
        <div className="card">
          <div className="card-header flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-violet-100 dark:bg-violet-900/30">
              <Sparkles className="w-4 h-4 text-violet-600 dark:text-violet-400" />
            </div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">AI Pricing Insights</h3>
          </div>
          <div className="card-body space-y-4">
            <div className="p-4 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-white">
              <div className="flex items-center gap-2 text-primary-100 text-xs font-medium mb-1">
                <TrendingUp className="w-3.5 h-3.5" /> Revenue Opportunity
              </div>
              <p className="text-2xl font-bold">{fmtMoney(revenueOpportunity)}</p>
              <p className="text-[11px] text-primary-100/80 mt-0.5">
                Potential additional revenue from {underpriced.length} pending price increases
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 mb-1">
                  <Target className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium">Optimization</span>
                </div>
                <p className="text-xl font-bold text-surface-900 dark:text-white">{pendingRecs.length}</p>
                <p className="text-[10px] text-surface-400">products awaiting review</p>
              </div>
              <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                <div className="flex items-center gap-1.5 text-sky-600 dark:text-sky-400 mb-1">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium">Underpriced</span>
                </div>
                <p className="text-xl font-bold text-surface-900 dark:text-white">{underpriced.length}</p>
                <p className="text-[10px] text-surface-400">price increase recommended</p>
              </div>
              <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                <div className="flex items-center gap-1.5 text-red-600 dark:text-red-400 mb-1">
                  <TrendingDown className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium">Overpriced</span>
                </div>
                <p className="text-xl font-bold text-surface-900 dark:text-white">{overpriced.length}</p>
                <p className="text-[10px] text-surface-400">price decrease recommended</p>
              </div>
              <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                <div className="flex items-center gap-1.5 text-violet-600 dark:text-violet-400 mb-1">
                  <Gauge className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium">Avg Uplift</span>
                </div>
                <p className="text-xl font-bold text-surface-900 dark:text-white">
                  {avgUplift !== null ? `${avgUplift.toFixed(1)}%` : '—'}
                </p>
                <p className="text-[10px] text-surface-400">predicted across pending recs</p>
              </div>
            </div>
            {lowConfidence.length > 0 && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/15 border border-amber-200 dark:border-amber-800/60">
                <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  {lowConfidence.length} recommendation{lowConfidence.length === 1 ? '' : 's'} below {LOW_CONFIDENCE_THRESHOLD}% confidence need manual review.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: Top Performing Products + Dataset Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Performing Products */}
        <div className="card lg:col-span-2 overflow-hidden">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
                <Crown className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Top Performing Products</h3>
            </div>
            <Link to="/products" className="text-xs text-primary-600 dark:text-primary-400 font-medium hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            {topRows.length === 0 ? (
              <EmptyState
                icon={Package}
                title="No products yet"
                hint="Import a dataset or add products to populate this ranking."
                cta={{ to: '/datasets', label: 'Upload a dataset' }}
              />
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-50 dark:bg-surface-800/50">
                    <th className="table-header">#</th>
                    <th className="table-header">Product</th>
                    <th className="table-header">Category</th>
                    <th className="table-header text-right">Price</th>
                    <th className="table-header text-right">Revenue</th>
                    <th className="table-header text-right">Margin</th>
                    <th className="table-header">AI Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                  {topRows.map((row) => (
                    <tr key={row.id} className="table-row">
                      <td className="table-cell">
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-surface-100 dark:bg-surface-700 text-xs font-bold text-surface-500 dark:text-surface-300">
                          {row.rank}
                        </span>
                      </td>
                      <td className="table-cell">
                        <p className="font-medium text-surface-900 dark:text-white">{row.name}</p>
                      </td>
                      <td className="table-cell">
                        <span className="badge-neutral">{row.category}</span>
                      </td>
                      <td className="table-cell text-right font-mono">{fmtMoney2(row.price)}</td>
                      <td className="table-cell text-right font-mono font-medium text-emerald-600 dark:text-emerald-400">{fmtMoney(row.revenue)}</td>
                      <td className="table-cell text-right font-mono">
                        {row.margin !== null ? (
                          <span className={row.margin >= 20 ? 'text-emerald-600 dark:text-emerald-400' : row.margin >= 0 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}>
                            {row.margin.toFixed(1)}%
                          </span>
                        ) : '—'}
                      </td>
                      <td className="table-cell">{statusBadge(row.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Dataset Health */}
        <div className="card">
          <div className="card-header flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-teal-100 dark:bg-teal-900/30">
              <ShieldCheck className="w-4 h-4 text-teal-600 dark:text-teal-400" />
            </div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Dataset Health</h3>
          </div>
          <div className="card-body">
            {!latestDataset ? (
              <EmptyState
                icon={Database}
                title="No dataset imported"
                hint="Upload and process a dataset to see its quality score and pipeline stats."
                cta={{ to: '/datasets', label: 'Upload a dataset' }}
              />
            ) : (
              <div className="space-y-5">
                <div className="flex items-center gap-5">
                  {/* Health ring */}
                  <div className="relative w-24 h-24 flex-shrink-0">
                    <svg viewBox="0 0 100 100" className="w-24 h-24 -rotate-90">
                      <circle cx="50" cy="50" r="42" fill="none" strokeWidth="10" className="stroke-surface-200 dark:stroke-surface-700" />
                      <circle
                        cx="50" cy="50" r="42" fill="none" strokeWidth="10" strokeLinecap="round"
                        stroke={latestDataset.health_score >= 80 ? '#10b981' : latestDataset.health_score >= 50 ? '#f59e0b' : '#ef4444'}
                        strokeDasharray={`${(latestDataset.health_score / 100) * 264} 264`}
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center">
                        <p className="text-xl font-bold text-surface-900 dark:text-white">{latestDataset.health_score ?? 0}%</p>
                      </div>
                    </div>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-surface-900 dark:text-white truncate">{latestDataset.name}</p>
                    <p className="text-xs text-surface-400 mt-0.5">{latestDataset.rows ?? 0} rows · {latestDataset.columns ?? 0} columns</p>
                    <span className="badge-success mt-2">{latestDataset.status || 'Processed'}</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-lg font-bold text-surface-900 dark:text-white">{latestDataset.missing_values ?? 0}</p>
                    <p className="text-[10px] text-surface-400">Missing Values</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-lg font-bold text-surface-900 dark:text-white">{latestDataset.duplicate_count ?? 0}</p>
                    <p className="text-[10px] text-surface-400">Duplicates Removed</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-lg font-bold text-surface-900 dark:text-white">{latestDataset.category_count ?? 0}</p>
                    <p className="text-[10px] text-surface-400">Categories</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-lg font-bold text-surface-900 dark:text-white">{fmtMoney2(latestDataset.avg_price ?? 0)}</p>
                    <p className="text-[10px] text-surface-400">Avg Price</p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-surface-400">
                  <span>Last import</span>
                  <span className="font-medium text-surface-600 dark:text-surface-300">
                    {latestDataset.created_at ? new Date(latestDataset.created_at).toLocaleDateString() : '—'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Pricing Recommendations + Model Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pricing Recommendations */}
        <div className="card lg:col-span-2 overflow-hidden">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                <Target className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Pricing Recommendations</h3>
            </div>
            <Link to="/ai" className="text-xs text-primary-600 dark:text-primary-400 font-medium hover:underline flex items-center gap-1">
              Run AI <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            {pendingRecs.length === 0 ? (
              <EmptyState
                icon={Target}
                title="No pricing recommendations available"
                hint="Run the AI engine on your products to generate price optimization suggestions."
                cta={{ to: '/ai', label: 'Open AI Price Prediction' }}
              />
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-50 dark:bg-surface-800/50">
                    <th className="table-header">Product</th>
                    <th className="table-header text-right">Current</th>
                    <th className="table-header text-right">Recommended</th>
                    <th className="table-header">Confidence</th>
                    <th className="table-header text-right">Δ Revenue</th>
                    <th className="table-header text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                  {pendingRecs.slice(0, 5).map((rec) => {
                    const changePct = ((rec.recommended_price - rec.current_price) / rec.current_price) * 100;
                    const confidence = rec.confidence_score ?? 0;
                    return (
                      <tr key={rec.id} className="table-row">
                        <td className="table-cell">
                          <p className="font-medium text-surface-900 dark:text-white">{rec.product_name}</p>
                        </td>
                        <td className="table-cell text-right font-mono">{fmtMoney2(rec.current_price)}</td>
                        <td className="table-cell text-right font-mono font-semibold text-primary-600 dark:text-primary-400">
                          {fmtMoney2(rec.recommended_price)}
                        </td>
                        <td className="table-cell">
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-surface-200 dark:bg-surface-700 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${confidence >= LOW_CONFIDENCE_THRESHOLD ? 'bg-emerald-500' : confidence >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                                style={{ width: `${Math.min(100, confidence)}%` }}
                              ></div>
                            </div>
                            <span className="text-xs font-medium">{confidence.toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="table-cell text-right font-mono">
                          <span className={`inline-flex items-center gap-1 text-xs font-medium ${changePct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                            {changePct >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                            {changePct >= 0 ? '+' : ''}{changePct.toFixed(1)}%
                          </span>
                        </td>
                        <td className="table-cell text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link to="/ai" className="btn-ghost btn-sm" title="View details">
                              View
                            </Link>
                            {isAdminOrPricing && (
                              <button
                                onClick={async () => {
                                  setApproving(rec.id);
                                  try {
                                    const res = await pricingAPI.approveRecommendation(rec.id);
                                    toast.success('Applied', res.data.message);
                                    fetchAll(true);
                                  } catch (err) {
                                    toast.error('Failed to apply', err.response?.data?.detail);
                                  } finally {
                                    setApproving(null);
                                  }
                                }}
                                disabled={approving === rec.id}
                                className="btn-success btn-sm"
                              >
                                {approving === rec.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                                Approve
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Model Performance */}
        <div className="card">
          <div className="card-header flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
              <Gauge className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            </div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Model Performance</h3>
          </div>
          <div className="card-body space-y-4">
            {!aiReady || modelRows.length === 0 ? (
              <EmptyState
                icon={BrainCircuit}
                title={aiStatus?.samples > 0 ? 'Model not ready' : 'AI engine not trained'}
                hint={`Upload a dataset with at least ${aiStatus?.min_samples_required ?? 10} products to train Random Forest, XGBoost & Linear Regression.`}
                cta={{ to: '/datasets', label: 'Upload a dataset' }}
              />
            ) : (
              <>
                <div className="p-4 rounded-xl bg-gradient-to-br from-violet-500 to-primary-600 text-white">
                  <div className="flex items-center gap-2 text-primary-100 text-xs font-medium mb-1">
                    <Sparkles className="w-3.5 h-3.5" /> Best Model
                  </div>
                  <p className="text-xl font-bold">{aiStatus.best_model}</p>
                  <p className="text-[11px] text-primary-100/80 mt-0.5">
                    Trained on {aiStatus.model_info?.dataset_name || 'your catalog'} · R² {aiStatus.accuracy ?? 0}
                  </p>
                </div>
                <div className="space-y-3">
                  {modelRows.map((m) => (
                    <div key={m.name}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-surface-700 dark:text-surface-300 flex items-center gap-1.5">
                          {m.isBest && <Crown className="w-3 h-3 text-amber-500" />}
                          {m.name}
                        </span>
                        <span className="text-xs font-mono text-surface-500">
                          R² {m.r2.toFixed(3)} · MAE {fmtMoney(m.mae)}
                        </span>
                      </div>
                      <div className="w-full bg-surface-200 dark:bg-surface-700 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full transition-all duration-500 ${m.isBest ? 'bg-violet-500' : 'bg-primary-500'}`}
                          style={{ width: `${Math.max(4, m.score)}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-lg font-bold text-surface-900 dark:text-white">{aiStatus.samples}</p>
                    <p className="text-[10px] text-surface-400">Training Records</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <p className="text-lg font-bold text-surface-900 dark:text-white truncate">
                      {aiStatus.model_info?.created_at
                        ? new Date(aiStatus.model_info.created_at).toLocaleDateString()
                        : '—'}
                    </p>
                    <p className="text-[10px] text-surface-400">Last Trained</p>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Row 4: Recent Activity (timeline) + Recent Imports */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity timeline */}
        <div className="card lg:col-span-2">
          <div className="card-header flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800/60">
              <Activity className="w-4 h-4 text-slate-500" />
            </div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Recent Activity</h3>
          </div>
          <div className="card-body">
            {activity.length === 0 ? (
              <EmptyState icon={Activity} title="No recent activity" hint="Actions across the platform will appear here." />
            ) : (
              <div className="relative pl-6">
                <div className="absolute left-[9px] top-2 bottom-2 w-px bg-surface-200 dark:bg-surface-700"></div>
                <div className="space-y-4">
                  {activity.map((log, i) => {
                    const { icon: Icon, tint } = activityMeta(log.action);
                    return (
                      <div key={log.id || i} className="relative">
                        <span className={`absolute -left-6 top-0.5 w-[19px] h-[19px] rounded-full flex items-center justify-center ring-4 ring-white dark:ring-surface-800 ${tint}`}>
                          <Icon className="w-3 h-3" />
                        </span>
                        <p className="text-sm text-surface-700 dark:text-surface-300">{log.action}</p>
                        <p className="text-xs text-surface-400 dark:text-surface-500 mt-0.5 truncate">
                          {log.details || `${log.resource_type || 'System'} #${log.resource_id || ''}`}
                        </p>
                        <p className="text-[10px] text-surface-400 mt-0.5">
                          {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Imports */}
        <div className="card">
          <div className="card-header flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-sky-100 dark:bg-sky-900/30">
              <Database className="w-4 h-4 text-sky-600 dark:text-sky-400" />
            </div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Recent Imports</h3>
          </div>
          <div className="card-body">
            {!data?.recent_imports?.length ? (
              <EmptyState
                icon={Database}
                title="No dataset imports yet"
                hint="Processed datasets will appear here with their health score."
                cta={{ to: '/datasets', label: 'Go to Dataset Management' }}
              />
            ) : (
              <div className="space-y-3">
                {data.recent_imports.map((imp, i) => (
                  <div key={imp.id || i} className="flex items-center justify-between gap-3 p-3 rounded-lg bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex-shrink-0">
                        <FileSpreadsheet className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-surface-900 dark:text-white truncate">{imp.name}</p>
                        <p className="text-xs text-surface-400">
                          {imp.rows} rows · health {imp.health_score ?? 0}%
                        </p>
                      </div>
                    </div>
                    <span className="badge-success flex-shrink-0">Processed</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
            <Boxes className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Quick Actions</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {quickActions.map(({ to, icon: Icon, label, desc }) => (
              <Link
                key={to}
                to={to}
                className="group flex flex-col gap-2 p-4 rounded-xl border border-surface-200 dark:border-surface-700 hover:border-primary-500 dark:hover:border-primary-500 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
              >
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-lg bg-primary-50 dark:bg-primary-900/20 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/40 transition-colors">
                    <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <ArrowRight className="w-4 h-4 text-surface-300 dark:text-surface-600 group-hover:text-primary-500 group-hover:translate-x-0.5 transition-all" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-surface-900 dark:text-white">{label}</p>
                  <p className="text-xs text-surface-400 mt-0.5">{desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
