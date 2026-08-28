import { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend, Area, AreaChart,
} from 'recharts';
import {
  TrendingUp, TrendingDown, DollarSign, ShoppingCart, BarChart3,
  AlertTriangle, Target, ArrowUpRight, ArrowDownRight, Minus,
  Search, ChevronUp, ChevronDown, Filter,
} from 'lucide-react';
import { profitabilityAPI } from '../api/client';

const PERIOD_OPTIONS = [
  { label: '7 Days', value: 7 },
  { label: '30 Days', value: 30 },
  { label: '90 Days', value: 90 },
  { label: 'All Time', value: null },
];

const CATEGORY_COLORS = [
  '#2563eb', '#7c3aed', '#059669', '#d97706', '#dc2626',
  '#0891b2', '#4f46e5', '#16a34a', '#ca8a04', '#9333ea',
];

function MetricCard({ label, value, prefix = '', suffix = '', icon: Icon, color = 'primary', subtitle }) {
  const colorMap = {
    primary: 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400',
    success: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400',
    danger: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400',
    warning: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400',
    info: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
  };
  return (
    <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-surface-500 dark:text-surface-400 uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-surface-900 dark:text-white mt-1 truncate">
            {prefix}{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}{suffix}
          </p>
          {subtitle && <p className="text-xs text-surface-500 mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-lg ${colorMap[color]}`}>
            <Icon size={20} />
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    'High Profitability': 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    'Moderate Profitability': 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    'Low Profitability': 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    'Loss': 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles['Low Profitability']}`}>
      {status}
    </span>
  );
}

function SortIcon({ column, sortBy, sortOrder }) {
  if (column !== sortBy) return null;
  return sortOrder === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
}

function SectionHeader({ title, subtitle }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-surface-900 dark:text-white">{title}</h2>
      {subtitle && <p className="text-sm text-surface-500 dark:text-surface-400 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function InsightCard({ insight }) {
  const severityStyles = {
    success: 'border-l-emerald-500 bg-emerald-50/50 dark:bg-emerald-900/10',
    warning: 'border-l-amber-500 bg-amber-50/50 dark:bg-amber-900/10',
    critical: 'border-l-red-500 bg-red-50/50 dark:bg-red-900/10',
    info: 'border-l-blue-500 bg-blue-50/50 dark:bg-blue-900/10',
  };
  return (
    <div className={`border-l-4 rounded-r-lg p-4 ${severityStyles[insight.severity] || severityStyles.info}`}>
      <p className="text-sm font-semibold text-surface-900 dark:text-white">{insight.title}</p>
      <p className="text-sm text-surface-600 dark:text-surface-300 mt-1">{insight.text}</p>
    </div>
  );
}

export default function Profitability() {
  const [period, setPeriod] = useState(null);
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState(null);
  const [products, setProducts] = useState(null);
  const [categories, setCategories] = useState([]);
  const [aiImpact, setAiImpact] = useState([]);
  const [opportunities, setOpportunities] = useState({ insights: [], alerts: [] });
  const [loading, setLoading] = useState(true);
  const [productSearch, setProductSearch] = useState('');
  const [sortBy, setSortBy] = useState('profit');
  const [sortOrder, setSortOrder] = useState('desc');
  const [productPage, setProductPage] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => {
    loadAll();
  }, [period]);

  useEffect(() => {
    loadProducts();
  }, [productSearch, sortBy, sortOrder, productPage]);

  async function loadAll() {
    setLoading(true);
    try {
      const [sumRes, trendRes, prodRes, catRes, aiRes, oppRes] = await Promise.all([
        profitabilityAPI.summary(period),
        profitabilityAPI.trends(period),
        profitabilityAPI.products({ days: period, sort_by: sortBy, sort_order: sortOrder, skip: productPage * PAGE_SIZE, limit: PAGE_SIZE }),
        profitabilityAPI.categories(period),
        profitabilityAPI.aiImpact(period, 20),
        profitabilityAPI.opportunities(period),
      ]);
      setSummary(sumRes.data);
      setTrends(trendRes.data);
      setProducts(prodRes.data);
      setCategories(catRes.data);
      setAiImpact(aiRes.data);
      setOpportunities(oppRes.data);
    } catch (err) {
      console.error('Failed to load profitability data', err);
    }
    setLoading(false);
  }

  async function loadProducts() {
    try {
      const res = await profitabilityAPI.products({
        days: period, search: productSearch || undefined,
        sort_by: sortBy, sort_order: sortOrder,
        skip: productPage * PAGE_SIZE, limit: PAGE_SIZE,
      });
      setProducts(res.data);
    } catch (err) {
      console.error('Failed to load products', err);
    }
  }

  function handleSort(col) {
    if (col === sortBy) {
      setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(col);
      setSortOrder('desc');
    }
    setProductPage(0);
  }

  if (loading && !summary) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-200 dark:bg-surface-700 rounded w-64" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-surface-200 dark:bg-surface-700 rounded-xl" />)}
          </div>
          <div className="h-80 bg-surface-200 dark:bg-surface-700 rounded-xl" />
        </div>
      </div>
    );
  }

  const fmt = (v) => v != null ? `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00';
  const fmtPct = (v) => v != null ? `${Number(v).toFixed(1)}%` : '0.0%';

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      {/* Header + Period Selector */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Profitability Analytics</h1>
          <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
            Revenue, cost, margin analysis and AI pricing profit impact
          </p>
        </div>
        <div className="flex gap-1 bg-surface-100 dark:bg-surface-800 rounded-lg p-1">
          {PERIOD_OPTIONS.map(opt => (
            <button
              key={opt.label}
              onClick={() => setPeriod(opt.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                period === opt.value
                  ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* A. KPI Row */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          <MetricCard label="Total Revenue" value={fmt(summary.total_revenue)} icon={DollarSign} color="primary" />
          <MetricCard label="Total Cost" value={fmt(summary.total_cost)} icon={ShoppingCart} color="warning" />
          <MetricCard label="Gross Profit" value={fmt(summary.gross_profit)} icon={TrendingUp} color="success"
            subtitle={`${summary.total_units_sold?.toLocaleString()} units sold`} />
          <MetricCard label="Profit Margin" value={fmtPct(summary.profit_margin)} icon={Target} color="info" />
          <MetricCard label="Avg Profit / Product" value={fmt(summary.average_profit_per_product)} icon={BarChart3} color="primary"
            subtitle={`${summary.products_with_sales} products with sales`} />
        </div>
      )}

      {/* Best / Lowest Products */}
      {summary && (summary.best_product || summary.lowest_product) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {summary.best_product && (
            <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600">
                  <ArrowUpRight size={16} />
                </div>
                <span className="text-xs font-medium text-surface-500 uppercase tracking-wider">Best Performing</span>
              </div>
              <p className="text-sm font-semibold text-surface-900 dark:text-white truncate">{summary.best_product.name}</p>
              <div className="flex gap-4 mt-1.5">
                <span className="text-xs text-surface-500">Profit: <span className="font-medium text-emerald-600">{fmt(summary.best_product.profit)}</span></span>
                <span className="text-xs text-surface-500">Margin: <span className="font-medium">{fmtPct(summary.best_product.margin_pct)}</span></span>
              </div>
            </div>
          )}
          {summary.lowest_product && (
            <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600">
                  <ArrowDownRight size={16} />
                </div>
                <span className="text-xs font-medium text-surface-500 uppercase tracking-wider">Lowest Profitability</span>
              </div>
              <p className="text-sm font-semibold text-surface-900 dark:text-white truncate">{summary.lowest_product.name}</p>
              <div className="flex gap-4 mt-1.5">
                <span className="text-xs text-surface-500">Profit: <span className="font-medium text-red-600">{fmt(summary.lowest_product.profit)}</span></span>
                <span className="text-xs text-surface-500">Margin: <span className="font-medium">{fmtPct(summary.lowest_product.margin_pct)}</span></span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* B. Profitability Trend */}
      {trends && trends.daily && trends.daily.length > 0 && (
        <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-5">
          <SectionHeader title="Revenue vs Cost vs Profit" subtitle={`${trends.point_count} data points`} />
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={trends.daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => { const dt = new Date(d); return `${dt.getMonth()+1}/${dt.getDate()}`; }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmt(v)} labelFormatter={d => new Date(d).toLocaleDateString()} />
              <Legend />
              <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#2563eb" fill="#2563eb" fillOpacity={0.1} strokeWidth={2} />
              <Area type="monotone" dataKey="cost" name="Cost" stroke="#d97706" fill="#d97706" fillOpacity={0.1} strokeWidth={2} />
              <Area type="monotone" dataKey="profit" name="Profit" stroke="#059669" fill="#059669" fillOpacity={0.1} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Margin Trend + Category Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Margin Trend */}
        {trends && trends.margin_trend && trends.margin_trend.length > 0 && (
          <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-5">
            <SectionHeader title="Profit Margin Trend" subtitle="Daily margin %" />
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trends.margin_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => { const dt = new Date(d); return `${dt.getMonth()+1}/${dt.getDate()}`; }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${v.toFixed(0)}%`} />
                <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} labelFormatter={d => new Date(d).toLocaleDateString()} />
                <Line type="monotone" dataKey="margin" name="Margin %" stroke="#4f46e5" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Profit by Category */}
        {categories.length > 0 && (
          <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-5">
            <SectionHeader title="Profit by Category" subtitle={`${categories.length} categories`} />
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={categories.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="category" tick={{ fontSize: 11 }} width={120} />
                <Tooltip formatter={(v) => fmt(v)} />
                <Bar dataKey="profit" name="Profit" radius={[0, 4, 4, 0]}>
                  {categories.slice(0, 10).map((_, i) => (
                    <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* C. Product Profitability Table */}
      {products && (
        <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <SectionHeader title="Product Profitability" subtitle={`${products.total} products`} />
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
              <input
                type="text"
                placeholder="Search products..."
                value={productSearch}
                onChange={e => { setProductSearch(e.target.value); setProductPage(0); }}
                className="pl-9 pr-3 py-2 text-sm border border-surface-200 dark:border-surface-600 rounded-lg bg-surface-50 dark:bg-surface-700 text-surface-900 dark:text-white w-64 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-200 dark:border-surface-700">
                  {[
                    { key: 'name', label: 'Product' },
                    { key: 'category', label: 'Category' },
                    { key: 'units', label: 'Units' },
                    { key: 'revenue', label: 'Revenue' },
                    { key: 'profit', label: 'Profit' },
                    { key: 'margin', label: 'Margin %' },
                    { key: 'status', label: 'Status' },
                  ].map(col => (
                    <th
                      key={col.key}
                      onClick={() => ['revenue', 'profit', 'margin', 'units', 'name'].includes(col.key) && handleSort(col.key)}
                      className={`px-3 py-2.5 text-left text-xs font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider ${['revenue', 'profit', 'margin', 'units', 'name'].includes(col.key) ? 'cursor-pointer hover:text-primary-600 select-none' : ''}`}
                    >
                      <span className="inline-flex items-center gap-1">
                        {col.label}
                        <SortIcon column={col.key} sortBy={sortBy} sortOrder={sortOrder} />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {products.items.map(p => (
                  <tr key={p.product_id} className="border-b border-surface-100 dark:border-surface-700/50 hover:bg-surface-50 dark:hover:bg-surface-700/30">
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-surface-900 dark:text-white truncate max-w-[200px]">{p.name}</div>
                      {p.brand && <div className="text-xs text-surface-400">{p.brand}</div>}
                    </td>
                    <td className="px-3 py-2.5 text-surface-600 dark:text-surface-300">{p.category}</td>
                    <td className="px-3 py-2.5 text-surface-600 dark:text-surface-300 font-mono">{p.units_sold.toLocaleString()}</td>
                    <td className="px-3 py-2.5 font-mono text-surface-900 dark:text-white">{fmt(p.revenue)}</td>
                    <td className={`px-3 py-2.5 font-mono font-medium ${p.profit >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {fmt(p.profit)}
                    </td>
                    <td className={`px-3 py-2.5 font-mono ${p.margin_pct >= 0 ? 'text-surface-600 dark:text-surface-300' : 'text-red-600'}`}>
                      {fmtPct(p.margin_pct)}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={p.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {products.total > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-surface-200 dark:border-surface-700">
              <span className="text-xs text-surface-500">
                Showing {productPage * PAGE_SIZE + 1}–{Math.min((productPage + 1) * PAGE_SIZE, products.total)} of {products.total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setProductPage(p => Math.max(0, p - 1))}
                  disabled={productPage === 0}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-surface-200 dark:border-surface-600 disabled:opacity-40 hover:bg-surface-50 dark:hover:bg-surface-700"
                >Previous</button>
                <button
                  onClick={() => setProductPage(p => p + 1)}
                  disabled={(productPage + 1) * PAGE_SIZE >= products.total}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-surface-200 dark:border-surface-600 disabled:opacity-40 hover:bg-surface-50 dark:hover:bg-surface-700"
                >Next</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* D. AI Pricing Profit Impact */}
      {aiImpact.length > 0 && (
        <div className="bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 p-5">
          <SectionHeader title="AI Pricing Profit Impact" subtitle="Current vs AI-recommended price profitability" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-200 dark:border-surface-700">
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Product</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Current Price</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">AI Price</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Current Margin</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Projected Margin</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Profit Change (30d)</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {aiImpact.map(a => (
                  <tr key={a.product_id} className="border-b border-surface-100 dark:border-surface-700/50 hover:bg-surface-50 dark:hover:bg-surface-700/30">
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-surface-900 dark:text-white truncate max-w-[200px]">{a.name}</div>
                      <div className="text-xs text-surface-400">{a.category}</div>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-surface-900 dark:text-white">{fmt(a.current_price)}</td>
                    <td className="px-3 py-2.5 text-right font-mono font-medium text-primary-600 dark:text-primary-400">{fmt(a.ai_price)}</td>
                    <td className="px-3 py-2.5 text-right font-mono">{fmtPct(a.current_margin)}</td>
                    <td className="px-3 py-2.5 text-right font-mono font-medium">{fmtPct(a.projected_margin)}</td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${a.profit_change >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {a.profit_change >= 0 ? '+' : ''}{fmt(a.profit_change)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-surface-600 dark:text-surface-300">{a.confidence.toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* E+F. Opportunities & Alerts */}
      {(opportunities.insights.length > 0 || opportunities.alerts.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {opportunities.insights.length > 0 && (
            <div className="space-y-3">
              <SectionHeader title="Profitability Opportunities" subtitle="Data-driven insights" />
              {opportunities.insights.map((ins, i) => <InsightCard key={i} insight={ins} />)}
            </div>
          )}
          {opportunities.alerts.length > 0 && (
            <div className="space-y-3">
              <SectionHeader title="Profitability Alerts" subtitle="Requires attention" />
              {opportunities.alerts.map((al, i) => <InsightCard key={i} insight={al} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
