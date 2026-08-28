import { useState, useEffect } from 'react';
import { biAPI } from '../api/client';
import { LayoutDashboard, TrendingUp, TrendingDown, Minus, AlertTriangle, Target, Shield, Package, BarChart3, RefreshCw, ArrowUpRight, ArrowDownRight, DollarSign, ShoppingCart, Users, Zap, CheckCircle, Clock } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

function StatCard({ label, value, sub, icon: Icon, color = 'text-blue-400', trend, trendValue }) {
  return (
    <div className="bg-surface-800/50 border border-surface-700/50 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {Icon && <div className={`p-1.5 rounded-lg bg-surface-700/50 ${color}`}><Icon size={16} /></div>}
          <span className="text-xs text-surface-400 uppercase tracking-wider">{label}</span>
        </div>
        {trend !== undefined && (
          <span className={`text-xs font-medium flex items-center gap-0.5 ${trend >= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {trend >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
            {trend >= 0 ? '+' : ''}{typeof trendValue === 'number' ? trendValue.toFixed(1) : trendValue}%
          </span>
        )}
      </div>
      <div className="text-2xl font-bold text-surface-100">{value}</div>
      {sub && <div className="text-xs text-surface-500 mt-1">{sub}</div>}
    </div>
  );
}

function AlertCard({ alert }) {
  const colors = {
    warning: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    info: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    success: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
    critical: 'bg-red-500/10 border-red-500/30 text-red-400',
  };
  const icons = {
    warning: AlertTriangle,
    info: Target,
    success: CheckCircle,
    critical: AlertTriangle,
  };
  const Icon = icons[alert.severity] || AlertTriangle;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${colors[alert.severity] || colors.info}`}>
      <Icon size={16} className="mt-0.5 shrink-0" />
      <div className="min-w-0">
        <div className="text-sm font-medium">{alert.title}</div>
        <div className="text-xs opacity-80 mt-0.5">{alert.detail}</div>
      </div>
    </div>
  );
}

function ActionRow({ action }) {
  const actionColors = {
    increase_price: 'text-emerald-400',
    decrease_price: 'text-amber-400',
    maintain_price: 'text-blue-400',
    promotional_pricing: 'text-purple-400',
  };
  const actionLabels = {
    increase_price: 'Increase Price',
    decrease_price: 'Decrease Price',
    maintain_price: 'Maintain',
    promotional_pricing: 'Promotional',
  };
  return (
    <div className="flex items-center justify-between py-2 border-b border-surface-700/30 last:border-0">
      <div className="min-w-0 flex-1">
        <div className="text-sm text-surface-200 truncate">{action.product_name}</div>
        <div className="text-xs text-surface-500">{action.category}</div>
      </div>
      <div className="text-right shrink-0 ml-3">
        <div className={`text-xs font-medium ${actionColors[action.action] || 'text-surface-400'}`}>
          {actionLabels[action.action] || action.action}
        </div>
        <div className="text-xs text-surface-500">{action.confidence?.toFixed(0)}% confidence</div>
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-surface-800 border border-surface-700/50 rounded-lg p-3 shadow-xl text-xs">
      <div className="text-surface-400 mb-1">{label}</div>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-surface-300">{entry.name}:</span>
          <span className="text-surface-100 font-medium">${Number(entry.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export default function ExecutiveBI() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('');
  const [error, setError] = useState(null);

  const fetchData = async (days) => {
    setLoading(true);
    setError(null);
    try {
      const res = await biAPI.summary(days || undefined);
      setData(res.data);
    } catch (err) {
      console.error('Failed to load executive BI:', err);
      setError('Failed to load executive business intelligence data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(period); }, [period]);

  const kpis = data?.kpis || {};
  const trend = data?.revenue_trend || {};
  const pricing = data?.pricing_performance || {};
  const market = data?.market_position || {};
  const demand = data?.demand_inventory || {};
  const actions = data?.priority_actions || [];
  const alerts = data?.alerts || [];
  const report = data?.executive_report || {};

  // Format chart data
  const chartData = (trend.points || []).map(p => ({
    date: p.date?.slice(5) || p.date,
    Revenue: p.revenue,
    Profit: p.profit,
  }));

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-100 flex items-center gap-2">
            <LayoutDashboard size={24} className="text-blue-400" />
            Executive Business Intelligence
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Management overview — revenue, profitability, pricing performance, demand, and strategic priorities
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-surface-800/50 border border-surface-700/50 rounded-lg overflow-hidden">
            {[
              { label: 'All', value: '' },
              { label: '7D', value: 7 },
              { label: '30D', value: 30 },
              { label: '90D', value: 90 },
            ].map((p) => (
              <button
                key={p.label}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  period === p.value ? 'bg-blue-600 text-white' : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => fetchData(period)}
            disabled={loading}
            className="p-2 bg-surface-800/50 border border-surface-700/50 rounded-lg text-surface-400 hover:text-surface-200 transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3 text-surface-400">
            <RefreshCw size={20} className="animate-spin" />
            Loading executive intelligence...
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center text-red-400">{error}</div>
      ) : data ? (
        <>
          {/* KPI ROW */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard
              label="Revenue"
              value={`$${(kpis.total_revenue || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              icon={DollarSign}
              color="text-blue-400"
              trend={trend.growth_pct}
              trendValue={trend.growth_pct}
            />
            <StatCard
              label="Profit"
              value={`$${(kpis.total_profit || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              icon={TrendingUp}
              color="text-emerald-400"
            />
            <StatCard
              label="Margin"
              value={`${(kpis.profit_margin || 0).toFixed(1)}%`}
              icon={BarChart3}
              color={kpis.profit_margin >= 20 ? 'text-emerald-400' : kpis.profit_margin >= 10 ? 'text-blue-400' : 'text-amber-400'}
            />
            <StatCard
              label="Products"
              value={kpis.products_analyzed || 0}
              sub={`${(kpis.total_units_sold || 0).toLocaleString()} units sold`}
              icon={Package}
            />
            <StatCard
              label="Priority Actions"
              value={kpis.high_priority_actions || 0}
              sub={`$${(kpis.potential_profit_uplift || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} potential uplift`}
              icon={Target}
              color="text-amber-400"
            />
            <StatCard
              label="Avg Price"
              value={`$${(kpis.average_selling_price || 0).toFixed(2)}`}
              icon={ShoppingCart}
              color="text-purple-400"
            />
          </div>

          {/* REVENUE & PROFITABILITY TREND */}
          {chartData.length > 0 && (
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4">Revenue & Profit Trend</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="profGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area type="monotone" dataKey="Revenue" stroke="#3b82f6" fill="url(#revGrad)" strokeWidth={2} />
                    <Area type="monotone" dataKey="Profit" stroke="#10b981" fill="url(#profGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* PRICING PERFORMANCE + MARKET + DEMAND (3 columns) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Pricing Performance */}
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4">Pricing Performance</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Price Increase Opportunities</span>
                  <span className="text-sm font-semibold text-emerald-400">{pricing.increase_opportunities}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Price Reduction Opportunities</span>
                  <span className="text-sm font-semibold text-amber-400">{pricing.decrease_opportunities}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Maintain Price</span>
                  <span className="text-sm font-semibold text-blue-400">{pricing.maintain_price}</span>
                </div>
                <div className="border-t border-surface-700/50 pt-3 flex items-center justify-between">
                  <span className="text-sm text-surface-300 font-medium">Potential Monthly Uplift</span>
                  <span className="text-lg font-bold text-emerald-400">${(pricing.potential_profit_uplift || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
                {/* Visual bar */}
                {pricing.total_recommendations > 0 && (
                  <div className="mt-2">
                    <div className="flex h-2 rounded-full overflow-hidden bg-surface-700">
                      <div className="bg-emerald-500" style={{ width: `${((pricing.increase_opportunities || 0) / pricing.total_recommendations) * 100}%` }} />
                      <div className="bg-amber-500" style={{ width: `${((pricing.decrease_opportunities || 0) / pricing.total_recommendations) * 100}%` }} />
                      <div className="bg-blue-500" style={{ width: `${((pricing.maintain_price || 0) / pricing.total_recommendations) * 100}%` }} />
                    </div>
                    <div className="flex justify-between mt-1 text-[10px] text-surface-500">
                      <span>Increase</span>
                      <span>Decrease</span>
                      <span>Maintain</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Market Position */}
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4">Market Position</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Below Competitive Range</span>
                  <span className="text-sm font-semibold text-emerald-400">{market.below_market}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Within Competitive Range</span>
                  <span className="text-sm font-semibold text-blue-400">{market.within_range}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Above Competitive Range</span>
                  <span className="text-sm font-semibold text-amber-400">{market.above_market}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Insufficient Data</span>
                  <span className="text-sm font-semibold text-surface-500">{market.insufficient_data}</span>
                </div>
                <div className="border-t border-surface-700/50 pt-3">
                  <p className="text-xs text-surface-500">{market.note}</p>
                </div>
              </div>
            </div>

            {/* Demand & Inventory */}
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4">Demand & Inventory</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Out of Stock</span>
                  <span className={`text-sm font-semibold ${demand.out_of_stock > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{demand.out_of_stock}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Low Stock (≤20)</span>
                  <span className={`text-sm font-semibold ${demand.low_stock > 5 ? 'text-amber-400' : 'text-surface-300'}`}>{demand.low_stock}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">Healthy Stock</span>
                  <span className="text-sm font-semibold text-emerald-400">{demand.healthy_stock}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-surface-400">High Stock (≥200)</span>
                  <span className="text-sm font-semibold text-surface-300">{demand.high_stock}</span>
                </div>
                {(demand.demand_signals || []).length > 0 && (
                  <div className="border-t border-surface-700/50 pt-3 space-y-1.5">
                    <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">Demand Signals</div>
                    {demand.demand_signals.slice(0, 5).map((d, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-xs text-surface-400 truncate max-w-[60%]">{d.name}</span>
                        <span className={`text-xs font-medium flex items-center gap-0.5 ${d.trend === 'up' ? 'text-emerald-400' : d.trend === 'down' ? 'text-amber-400' : 'text-blue-400'}`}>
                          {d.trend === 'up' ? <TrendingUp size={10} /> : d.trend === 'down' ? <TrendingDown size={10} /> : <Minus size={10} />}
                          {d.growth_pct > 0 ? '+' : ''}{d.growth_pct}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* PRIORITY ACTIONS + ALERTS (2 columns) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Priority Actions */}
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Target size={14} className="text-amber-400" />
                Priority Actions
              </h2>
              {actions.length === 0 ? (
                <p className="text-sm text-surface-500 text-center py-6">No priority actions at this time.</p>
              ) : (
                <div className="space-y-0">
                  {actions.slice(0, 10).map((action, i) => (
                    <ActionRow key={i} action={action} />
                  ))}
                </div>
              )}
            </div>

            {/* Alerts */}
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <AlertTriangle size={14} className="text-amber-400" />
                Business Health Alerts
              </h2>
              {alerts.length === 0 ? (
                <p className="text-sm text-surface-500 text-center py-6">No alerts — business is healthy.</p>
              ) : (
                <div className="space-y-2">
                  {alerts.map((alert, i) => (
                    <AlertCard key={i} alert={alert} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* EXECUTIVE REPORT */}
          {report.revenue && (
            <div className="bg-surface-800/30 border border-surface-700/50 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4">Executive Summary</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { label: 'Revenue', value: report.revenue, color: 'border-l-blue-500' },
                  { label: 'Profitability', value: report.profitability, color: 'border-l-emerald-500' },
                  { label: 'Pricing', value: report.pricing, color: 'border-l-purple-500' },
                  { label: 'Demand', value: report.demand, color: 'border-l-amber-500' },
                  { label: 'Market', value: report.market, color: 'border-l-cyan-500' },
                  { label: 'Priority Action', value: report.priority_action, color: 'border-l-red-500' },
                ].map((item, i) => (
                  <div key={i} className={`border-l-2 ${item.color} pl-4 py-2`}>
                    <div className="text-xs text-surface-400 uppercase tracking-wider mb-1">{item.label}</div>
                    <p className="text-sm text-surface-200 leading-relaxed">{item.value}</p>
                  </div>
                ))}
              </div>
              {report.risks && (
                <div className="mt-4 pt-4 border-t border-surface-700/50">
                  <div className="text-xs text-surface-400 uppercase tracking-wider mb-1">Risk Assessment</div>
                  <p className="text-sm text-surface-300">{report.risks}</p>
                </div>
              )}
            </div>
          )}

          {/* TOP PERFORMERS */}
          {kpis.best_product && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-5">
                <div className="text-xs text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <TrendingUp size={12} /> Best Performing Product
                </div>
                <div className="text-lg font-bold text-surface-100">{kpis.best_product.name}</div>
                <div className="text-sm text-surface-300 mt-1">
                  ${kpis.best_product.profit?.toLocaleString(undefined, { maximumFractionDigits: 0 })} profit
                  <span className="text-surface-500 mx-1">•</span>
                  {kpis.best_product.margin_pct?.toFixed(1)}% margin
                  <span className="text-surface-500 mx-1">•</span>
                  ${kpis.best_product.revenue?.toLocaleString(undefined, { maximumFractionDigits: 0 })} revenue
                </div>
              </div>
              {kpis.lowest_product && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-5">
                  <div className="text-xs text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <TrendingDown size={12} /> Lowest Performing Product
                  </div>
                  <div className="text-lg font-bold text-surface-100">{kpis.lowest_product.name}</div>
                  <div className="text-sm text-surface-300 mt-1">
                    ${kpis.lowest_product.profit?.toLocaleString(undefined, { maximumFractionDigits: 0 })} profit
                    <span className="text-surface-500 mx-1">•</span>
                    {kpis.lowest_product.margin_pct?.toFixed(1)}% margin
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
