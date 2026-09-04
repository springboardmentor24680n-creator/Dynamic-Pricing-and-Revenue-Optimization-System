import { useState, useEffect, useCallback, useRef } from 'react';
import { pricingStrategyAPI } from '../api/client';
import { Target, TrendingUp, TrendingDown, Minus, AlertTriangle, Search, ChevronDown, ChevronRight, ArrowUp, ArrowDown, Filter, BarChart3, Shield, RefreshCw, Zap, Eye, CheckCircle } from 'lucide-react';

const ACTION_CONFIG = {
  increase_price: { label: 'Increase Price', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', icon: TrendingUp },
  decrease_price: { label: 'Decrease Price', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', icon: TrendingDown },
  maintain_price: { label: 'Maintain Price', color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: Minus },
  promotional_pricing: { label: 'Promotional', color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30', icon: Zap },
};

const PRIORITY_CONFIG = {
  HIGH: { label: 'HIGH', color: 'text-red-400', bg: 'bg-red-500/10' },
  MEDIUM: { label: 'MEDIUM', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  LOW: { label: 'LOW', color: 'text-surface-400', bg: 'bg-surface-500/10' },
};

const MARKET_POSITION_LABELS = {
  below_market: { label: 'Below Market', color: 'text-emerald-400' },
  at_market: { label: 'At Market', color: 'text-blue-400' },
  within_range: { label: 'Within Range', color: 'text-blue-300' },
  above_market: { label: 'Above Market', color: 'text-amber-400' },
  unknown: { label: 'No Data', color: 'text-surface-500' },
};

const DEMAND_ICONS = { up: TrendingUp, down: TrendingDown, stable: Minus };
const DEMAND_COLORS = { up: 'text-emerald-400', down: 'text-amber-400', stable: 'text-blue-400' };

function StatCard({ label, value, sub, icon: Icon, color = 'text-blue-400' }) {
  return (
    <div className="bg-surface-800/50 border border-surface-700/50 rounded-xl p-4">
      <div className="flex items-center gap-3">
        {Icon && <div className={`p-2 rounded-lg bg-surface-700/50 ${color}`}><Icon size={18} /></div>}
        <div>
          <div className="text-xs text-surface-400 uppercase tracking-wider">{label}</div>
          <div className="text-xl font-bold text-surface-100">{value}</div>
          {sub && <div className="text-xs text-surface-500">{sub}</div>}
        </div>
      </div>
    </div>
  );
}

function PriorityBadge({ priority }) {
  const config = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.LOW;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${config.color} ${config.bg}`}>
      {config.label}
    </span>
  );
}

function ActionBadge({ action }) {
  const config = ACTION_CONFIG[action] || ACTION_CONFIG.maintain_price;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${config.color} ${config.bg} border ${config.border}`}>
      <Icon size={12} />
      {config.label}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const color = value >= 80 ? 'bg-emerald-500' : value >= 60 ? 'bg-blue-500' : value >= 40 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-surface-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="text-xs text-surface-300 font-mono">{value.toFixed(0)}%</span>
    </div>
  );
}

function MarketPositionBadge({ position }) {
  const config = MARKET_POSITION_LABELS[position] || MARKET_POSITION_LABELS.unknown;
  return <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>;
}

function DemandBadge({ trend, growth }) {
  const Icon = DEMAND_ICONS[trend] || Minus;
  const color = DEMAND_COLORS[trend] || 'text-surface-400';
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${color}`}>
      <Icon size={12} />
      {growth > 0 ? '+' : ''}{growth?.toFixed(1) || 0}%
    </span>
  );
}

export default function PricingStrategy() {
  const [recommendations, setRecommendations] = useState([]);
  const [summary, setSummary] = useState(null);
  const [categories, setCategories] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortBy, setSortBy] = useState('priority');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState(null);

  // Debounced search: each keystroke would otherwise fire a ~10-20s backend
  // recommendation recompute. 400ms after the user stops typing is enough to
  // collapse a fast typist's 10+ requests into one.
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setPage(0); }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchSeq = useRef(0);
  const fetchData = useCallback(async () => {
    const seq = ++fetchSeq.current;
    setLoading(true);
    setError(null);
    try {
      const [recRes, catRes] = await Promise.all([
        pricingStrategyAPI.recommendations({
          category: categoryFilter || undefined,
          search: search || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          skip: page,
          limit: 25,
        }),
        pricingStrategyAPI.categories(),
      ]);
      if (seq !== fetchSeq.current) return; // a newer request superseded this one
      setRecommendations(recRes.data.items || []);
      setSummary(recRes.data.summary || null);
      setTotal(recRes.data.total || 0);
      setCategories(catRes.data || []);
    } catch (err) {
      if (seq !== fetchSeq.current) return;
      console.error('Failed to load pricing strategy:', err);
      setError('Failed to load pricing strategy recommendations.');
    } finally {
      if (seq === fetchSeq.current) setLoading(false);
    }
  }, [categoryFilter, search, sortBy, sortOrder, page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSelectProduct = async (productId) => {
    if (selected?.product_id === productId) {
      setSelected(null);
      return;
    }
    setLoadingDetail(true);
    try {
      const res = await pricingStrategyAPI.productRecommendation(productId);
      setSelected(res.data);
    } catch (err) {
      console.error('Failed to load recommendation:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(0);
  };

  const SortIcon = ({ field }) => {
    if (sortBy !== field) return null;
    return sortOrder === 'desc' ? <ChevronDown size={14} /> : <ChevronRight size={14} />;
  };

  const totalPages = Math.ceil(total / 25);

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-100 flex items-center gap-2">
            <Target size={24} className="text-blue-400" />
            Pricing Strategy Recommendations
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Data-driven pricing actions with evidence from AI predictions, market intelligence, and profitability analytics
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* SUMMARY KPIs */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Total" value={summary.total_recommendations} icon={BarChart3} />
          <StatCard label="Increase" value={summary.price_increase_opportunities} icon={TrendingUp} color="text-emerald-400" />
          <StatCard label="Decrease" value={summary.price_reduction_opportunities} icon={TrendingDown} color="text-amber-400" />
          <StatCard label="Maintain" value={summary.maintain_price} icon={Shield} color="text-blue-400" />
          <StatCard label="Promotional" value={summary.promotional_pricing} icon={Zap} color="text-purple-400" />
          <StatCard label="High Priority" value={summary.high_priority_actions} icon={AlertTriangle} color="text-red-400" />
          <StatCard label="Profit Uplift" value={`$${(summary.total_potential_profit_uplift || 0).toLocaleString()}`} sub="monthly potential" icon={TrendingUp} color="text-emerald-400" />
        </div>
      )}

      {/* TOP PRIORITY ACTIONS */}
      {!loading && recommendations.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider flex items-center gap-2">
            <AlertTriangle size={14} className="text-amber-400" />
            Top Priority Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {recommendations.filter(r => r.priority === 'HIGH').slice(0, 6).map((rec) => (
              <button
                key={rec.product_id}
                onClick={() => handleSelectProduct(rec.product_id)}
                className={`text-left p-4 rounded-xl border transition-all hover:border-blue-500/50 ${
                  selected?.product_id === rec.product_id
                    ? 'bg-blue-500/10 border-blue-500/30'
                    : 'bg-surface-800/50 border-surface-700/50 hover:bg-surface-800/80'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="text-sm font-medium text-surface-200 truncate pr-2">{rec.product_name}</div>
                  <PriorityBadge priority={rec.priority} />
                </div>
                <div className="flex items-center gap-3 mb-2">
                  <ActionBadge action={rec.action} />
                  <span className="text-xs text-surface-400">{rec.category}</span>
                </div>
                <div className="text-xs text-surface-400 line-clamp-2">{rec.recommendation}</div>
                <div className="mt-2 flex items-center justify-between">
                  <ConfidenceBar value={rec.confidence} />
                  <span className={`text-xs font-medium ${rec.expected_impact?.profit_change >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {rec.expected_impact?.profit_change >= 0 ? '+' : ''}${(rec.expected_impact?.profit_change || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}/mo
                  </span>
                </div>
              </button>
            ))}
            {recommendations.filter(r => r.priority === 'HIGH').length === 0 && (
              <div className="col-span-full text-center py-6 text-surface-500 text-sm">
                No high-priority actions at this time. All products are well-positioned.
              </div>
            )}
          </div>
        </div>
      )}

      {/* FILTERS + TABLE */}
      <div className="space-y-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" />
            <input
              type="text"
              placeholder="Search products..."
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); }}
              className="w-full pl-9 pr-3 py-2 bg-surface-800/50 border border-surface-700/50 rounded-lg text-sm text-surface-200 placeholder-surface-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(0); }}
            className="px-3 py-2 bg-surface-800/50 border border-surface-700/50 rounded-lg text-sm text-surface-200 focus:outline-none focus:border-blue-500/50"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.category} value={c.category}>{c.category} ({c.count})</option>
            ))}
          </select>
          <span className="text-xs text-surface-500">{total} products</span>
        </div>

        {/* TABLE */}
        <div className="overflow-x-auto bg-surface-800/30 border border-surface-700/50 rounded-xl">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700/50">
                {[
                  { key: 'priority', label: 'Priority', w: 'w-20' },
                  { key: 'name', label: 'Product', w: 'w-[22%]' },
                  { key: 'action', label: 'Action', w: 'w-32' },
                  { key: 'price', label: 'Price', w: 'w-24' },
                  { key: 'margin', label: 'Margin', w: 'w-20' },
                  { key: 'demand', label: 'Demand', w: 'w-24' },
                  { key: 'market', label: 'Market', w: 'w-24' },
                  { key: 'impact', label: 'Impact', w: 'w-28' },
                  { key: 'confidence', label: 'Confidence', w: 'w-28' },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`px-3 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider cursor-pointer hover:text-surface-200 select-none ${col.w}`}
                  >
                    <span className="flex items-center gap-1">
                      {col.label}
                      <SortIcon field={col.key} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} className="px-6 py-12 text-center text-surface-500">
                  <div className="flex items-center justify-center gap-2">
                    <RefreshCw size={16} className="animate-spin" />
                    Loading recommendations...
                  </div>
                </td></tr>
              ) : recommendations.length === 0 ? (
                <tr><td colSpan={9} className="px-6 py-12 text-center text-surface-500">
                  No recommendations found.
                </td></tr>
              ) : (
                recommendations.map((rec) => (
                  <tr
                    key={rec.product_id}
                    onClick={() => handleSelectProduct(rec.product_id)}
                    className={`border-b border-surface-700/30 cursor-pointer transition-colors ${
                      selected?.product_id === rec.product_id
                        ? 'bg-blue-500/10'
                        : 'hover:bg-surface-800/50'
                    }`}
                  >
                    <td className="px-3 py-3"><PriorityBadge priority={rec.priority} /></td>
                    <td className="px-3 py-3">
                      <div className="font-medium text-surface-200 truncate">{rec.product_name}</div>
                      <div className="text-xs text-surface-500">{rec.brand || rec.category}</div>
                    </td>
                    <td className="px-3 py-3"><ActionBadge action={rec.action} /></td>
                    <td className="px-3 py-3">
                      <div className="text-surface-200 font-mono">${rec.current_price?.toFixed(2)}</div>
                      {rec.recommended_price !== rec.current_price && (
                        <div className={`text-xs font-mono ${rec.recommended_price > rec.current_price ? 'text-emerald-400' : 'text-amber-400'}`}>
                          → ${rec.recommended_price?.toFixed(2)}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <span className={`font-mono text-xs ${
                        rec.current_margin >= 20 ? 'text-emerald-400' :
                        rec.current_margin >= 10 ? 'text-blue-400' :
                        rec.current_margin >= 0 ? 'text-amber-400' : 'text-red-400'
                      }`}>
                        {rec.current_margin?.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-3 py-3"><DemandBadge trend={rec.demand_trend} growth={rec.demand_growth_pct} /></td>
                    <td className="px-3 py-3"><MarketPositionBadge position={rec.market_position} /></td>
                    <td className="px-3 py-3">
                      <span className={`text-xs font-medium ${(rec.expected_impact?.profit_change || 0) >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {(rec.expected_impact?.profit_change || 0) >= 0 ? '+' : ''}${(rec.expected_impact?.profit_change || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </td>
                    <td className="px-3 py-3"><ConfidenceBar value={rec.confidence} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* PAGINATION */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-surface-500">
              Showing {page + 1}–{Math.min(page + 25, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(0, page - 25))}
                disabled={page === 0}
                className="px-3 py-1 bg-surface-800/50 border border-surface-700/50 rounded text-xs text-surface-300 hover:bg-surface-700/50 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-xs text-surface-500">{page / 25 + 1} / {totalPages}</span>
              <button
                onClick={() => setPage(Math.min((totalPages - 1) * 25, page + 25))}
                disabled={page >= (totalPages - 1) * 25}
                className="px-3 py-1 bg-surface-800/50 border border-surface-700/50 rounded text-xs text-surface-300 hover:bg-surface-700/50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* SELECTED PRODUCT DETAIL */}
      {selected && (
        <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl overflow-hidden">
          {/* Detail Header */}
          <div className="px-6 py-4 border-b border-surface-700/50 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-surface-100">{selected.product_name}</h3>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-surface-400">{selected.category}</span>
                {selected.brand && <span className="text-xs text-surface-500">•</span>}
                {selected.brand && <span className="text-xs text-surface-400">{selected.brand}</span>}
                <ActionBadge action={selected.action} />
                <PriorityBadge priority={selected.priority} />
              </div>
            </div>
            <button onClick={() => setSelected(null)} className="text-surface-500 hover:text-surface-300 text-sm">Close</button>
          </div>

          <div className="p-6 space-y-6">
            {/* Price Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-700/30 rounded-lg p-4">
                <div className="text-xs text-surface-400 mb-1">Current Price</div>
                <div className="text-xl font-bold text-surface-100">${selected.current_price?.toFixed(2)}</div>
              </div>
              <div className="bg-surface-700/30 rounded-lg p-4">
                <div className="text-xs text-surface-400 mb-1">Recommended Price</div>
                <div className={`text-xl font-bold ${(selected.recommended_price || 0) > selected.current_price ? 'text-emerald-400' : (selected.recommended_price || 0) < selected.current_price ? 'text-amber-400' : 'text-blue-400'}`}>
                  ${selected.recommended_price?.toFixed(2)}
                </div>
              </div>
              <div className="bg-surface-700/30 rounded-lg p-4">
                <div className="text-xs text-surface-400 mb-1">Current Margin</div>
                <div className={`text-xl font-bold ${
                  selected.current_margin >= 20 ? 'text-emerald-400' :
                  selected.current_margin >= 10 ? 'text-blue-400' :
                  selected.current_margin >= 0 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {selected.current_margin?.toFixed(1)}%
                </div>
              </div>
              <div className="bg-surface-700/30 rounded-lg p-4">
                <div className="text-xs text-surface-400 mb-1">Confidence</div>
                <div className="text-xl font-bold text-surface-100">{selected.confidence?.toFixed(0)}%</div>
              </div>
            </div>

            {/* Two-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Recommendation + Factors */}
              <div className="space-y-4">
                {/* Recommendation */}
                <div className="bg-surface-700/30 rounded-lg p-4">
                  <div className="text-xs text-surface-400 uppercase tracking-wider mb-2">Recommendation</div>
                  <p className="text-sm text-surface-200 leading-relaxed">{selected.recommendation}</p>
                </div>

                {/* Why This Price */}
                <div className="bg-surface-700/30 rounded-lg p-4">
                  <div className="text-xs text-surface-400 uppercase tracking-wider mb-3">Why This Price?</div>
                  <div className="space-y-3">
                    {(selected.factors || []).slice(0, 5).map((factor, i) => (
                      <div key={i} className="flex items-start gap-3">
                        <div className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-sm font-medium text-surface-200">{factor.factor}</span>
                            <span className="text-xs text-surface-400 ml-2 shrink-0">{factor.impact}</span>
                          </div>
                          <p className="text-xs text-surface-400 leading-relaxed">{factor.explanation}</p>
                        </div>
                      </div>
                    ))}
                    {(!selected.factors || selected.factors.length === 0) && (
                      <p className="text-xs text-surface-500">No significant factors identified.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Right: Expected Impact + Data */}
              <div className="space-y-4">
                {/* Expected Impact */}
                <div className="bg-surface-700/30 rounded-lg p-4">
                  <div className="text-xs text-surface-400 uppercase tracking-wider mb-3">Expected Impact</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-surface-800/50 rounded-lg p-3">
                      <div className="text-xs text-surface-500">Current Revenue (30d)</div>
                      <div className="text-sm font-semibold text-surface-200">${(selected.expected_impact?.current_revenue_30d || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                    </div>
                    <div className="bg-surface-800/50 rounded-lg p-3">
                      <div className="text-xs text-surface-500">Projected Revenue (30d)</div>
                      <div className="text-sm font-semibold text-surface-200">${(selected.expected_impact?.projected_revenue_30d || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                    </div>
                    <div className="bg-surface-800/50 rounded-lg p-3">
                      <div className="text-xs text-surface-500">Revenue Change</div>
                      <div className={`text-sm font-semibold ${(selected.expected_impact?.revenue_change || 0) >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {(selected.expected_impact?.revenue_change || 0) >= 0 ? '+' : ''}${(selected.expected_impact?.revenue_change || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </div>
                    </div>
                    <div className="bg-surface-800/50 rounded-lg p-3">
                      <div className="text-xs text-surface-500">Profit Change (30d)</div>
                      <div className={`text-sm font-semibold ${(selected.expected_impact?.profit_change || 0) >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {(selected.expected_impact?.profit_change || 0) >= 0 ? '+' : ''}${(selected.expected_impact?.profit_change || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        <span className="text-xs ml-1">({(selected.expected_impact?.profit_change_pct || 0) >= 0 ? '+' : ''}{(selected.expected_impact?.profit_change_pct || 0).toFixed(1)}%)</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Market & Demand Data */}
                <div className="bg-surface-700/30 rounded-lg p-4">
                  <div className="text-xs text-surface-400 uppercase tracking-wider mb-3">Market & Demand Data</div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-surface-400">Demand Trend</span>
                      <DemandBadge trend={selected.demand_trend} growth={selected.demand_growth_pct} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-surface-400">Market Position</span>
                      <MarketPositionBadge position={selected.market_position} />
                    </div>
                    {selected.competitor_range?.lowest > 0 && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-surface-400">Competitor Range</span>
                          <span className="text-xs text-surface-300 font-mono">
                            ${selected.competitor_range.lowest.toFixed(2)} – ${selected.competitor_range.highest.toFixed(2)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-surface-400">Market Average</span>
                          <span className="text-xs text-surface-300 font-mono">${selected.competitor_range.average.toFixed(2)}</span>
                        </div>
                      </>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-surface-400">Stock Level</span>
                      <span className={`text-xs font-medium ${selected.stock_quantity <= 0 ? 'text-red-400' : selected.stock_quantity <= 20 ? 'text-amber-400' : 'text-surface-300'}`}>
                        {selected.stock_quantity} units
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-surface-400">Forecast Confidence</span>
                      <span className="text-xs text-surface-300">{selected.forecast_confidence?.toFixed(0) || 0}%</span>
                    </div>
                  </div>
                </div>

                {/* Cost Price */}
                <div className="bg-surface-700/30 rounded-lg p-4">
                  <div className="text-xs text-surface-400 uppercase tracking-wider mb-2">Cost & Pricing</div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-surface-400">Cost Price</span>
                      <span className="text-xs text-surface-300 font-mono">${selected.cost_price?.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-surface-400">Expected Units (30d)</span>
                      <span className="text-xs text-surface-300">{(selected.expected_impact?.units_30d || 0).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
