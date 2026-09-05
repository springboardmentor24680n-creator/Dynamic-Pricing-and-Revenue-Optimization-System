import React, { useState, useEffect } from "react";
import axios from "axios";

export default function PricingStrategyRecommendations({
  products,
  token,
  API,
  showToast,
  formatCurrency: propFormatCurrency
}) {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [strategyData, setStrategyData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const formatCurrency = (val) => {
    if (typeof val !== 'number') return val;
    if (propFormatCurrency) return propFormatCurrency(val);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  // Set default product on load
  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      setSelectedProductId(products[0].id);
    }
  }, [products, selectedProductId]);

  const handleGenerateStrategy = async () => {
    if (!selectedProductId) {
      showToast("Please select a product first.", "error");
      return;
    }

    setLoading(true);
    setError("");
    setStrategyData(null);

    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.get(`${API}/api/pricing-strategy/${selectedProductId}`, { headers });
      setStrategyData(res.data);
      showToast("Pricing strategy generated successfully.", "success");
    } catch (err) {
      console.error("Error generating pricing strategy:", err);
      const detail = err.response?.data?.detail || "Failed to generate pricing strategy.";
      setError(detail);
      showToast(detail, "error");
    } finally {
      setLoading(false);
    }
  };

  const getStrategyColorClass = (strategy) => {
    if (!strategy) return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200";
    const s = strategy.toUpperCase();
    if (s.includes("INCREASE") || s.includes("PREMIUM")) {
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/40";
    }
    if (s.includes("DECREASE") || s.includes("CLEARANCE") || s.includes("REDUCTION")) {
      return "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400 border border-rose-200 dark:border-rose-900/40";
    }
    if (s.includes("DEMAND") || s.includes("SEASONAL")) {
      return "bg-violet-100 text-violet-800 dark:bg-violet-950/40 dark:text-violet-400 border border-violet-200 dark:border-violet-900/40";
    }
    return "bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-900/40";
  };

  const getRiskColorClass = (risk) => {
    if (!risk) return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200";
    const r = risk.toUpperCase();
    if (r === "LOW") {
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-250 dark:border-emerald-900/40";
    }
    if (r === "HIGH") {
      return "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400 border border-rose-250 dark:border-rose-900/40";
    }
    return "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-250 dark:border-amber-900/40";
  };

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="panel-title panel-title-row">
        <div>
          <p className="eyebrow uppercase tracking-wider text-violet-600 dark:text-violet-400">Pricing Strategy</p>
          <h2 className="text-2xl font-extrabold text-slate-900 dark:text-white mt-1">Pricing Strategy Recommendations</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            Generate data-driven pricing strategies using market, competitor, demand, inventory and profitability signals.
          </p>
        </div>
      </div>

      {/* Selection Control Panel */}
      <div className="dashboard-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex-1 max-w-md">
          <label htmlFor="strategy-product-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
            Select Product
          </label>
          <select
            id="strategy-product-select"
            value={selectedProductId}
            onChange={(e) => {
              setSelectedProductId(e.target.value);
              setStrategyData(null);
              setError("");
            }}
            className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
          >
            <option value="">-- Choose a Product --</option>
            {products && products.map((prod) => (
              <option key={prod.id} value={prod.id}>
                {prod.name} ({prod.id})
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={handleGenerateStrategy}
          disabled={loading || !selectedProductId}
          className="px-6 py-2.5 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-400 disabled:cursor-not-allowed text-white font-bold text-sm rounded-xl cursor-pointer transition shadow-sm flex items-center justify-center gap-2 h-[42px]"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              Generating Strategy...
            </>
          ) : (
            "Generate Pricing Strategy"
          )}
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500 bg-white dark:bg-slate-900 border border-slate-250 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="w-10 h-10 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-4 font-semibold">Running multi-horizon pricing models...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl p-6 text-center space-y-3">
          <p className="text-sm font-semibold text-rose-700 dark:text-rose-400">{error}</p>
          <button
            type="button"
            onClick={handleGenerateStrategy}
            className="px-4 py-2 bg-violet-600 text-white rounded-xl text-xs font-bold hover:bg-violet-750"
          >
            Retry Generation
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !strategyData && !error && (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm border-dashed">
          <div className="p-4 bg-violet-50 dark:bg-slate-800/40 rounded-full text-violet-600 dark:text-violet-400">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-slate-800 dark:text-white mt-4">Select a product to generate a pricing strategy</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs">
            Review model calculations combining competitors, margins, demand forecasts, and seasonal status.
          </p>
        </div>
      )}

      {/* Complete Recommendation Display */}
      {strategyData && (
        <div className="space-y-6 animate-fade-in">
          {/* Main Layout Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Recommendation Summary Card */}
            <div className="lg:col-span-2 space-y-6">
              <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/5 rounded-full filter blur-xl"></div>
                <div className="border-b border-slate-100 dark:border-slate-800 pb-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">RECOMMENDED PRICING STRATEGY</p>
                  <h3 className="text-lg font-bold text-slate-800 dark:text-white mt-1">Optimization Core</h3>
                </div>

                <div className="flex flex-wrap items-center gap-4 justify-between">
                  <div>
                    <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">Strategy Type</span>
                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold mt-1.5 ${getStrategyColorClass(strategyData.strategy)}`}>
                      {strategyData.strategy}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">Risk Level</span>
                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold mt-1.5 ${getRiskColorClass(strategyData.risk_level)}`}>
                      {strategyData.risk_level}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">Model Confidence</span>
                    <div className="flex items-center gap-2 mt-1.5">
                      <div className="w-16 bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="bg-violet-600 h-2 rounded-full" style={{ width: `${strategyData.confidence}%` }}></div>
                      </div>
                      <span className="text-xs font-bold text-slate-700 dark:text-slate-350">{strategyData.confidence}%</span>
                    </div>
                  </div>
                </div>

                {/* Price Display Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 bg-slate-50/50 dark:bg-slate-950/20 p-5 rounded-2xl border border-slate-100 dark:border-slate-850">
                  <div>
                    <span className="text-xs text-slate-400 block">Current Price</span>
                    <strong className="text-lg font-bold text-slate-650 dark:text-slate-300 block mt-1">{formatCurrency(strategyData.current_price)}</strong>
                  </div>
                  <div className="sm:border-l sm:border-r border-slate-200 dark:border-slate-800 sm:px-6">
                    <span className="text-xs text-violet-600 dark:text-violet-400 block font-bold">Recommended Price</span>
                    <strong className="text-3xl font-extrabold text-violet-600 dark:text-violet-400 block mt-0.5">{formatCurrency(strategyData.recommended_price)}</strong>
                  </div>
                  <div className="sm:pl-6">
                    <span className="text-xs text-slate-400 block">Price Change</span>
                    <strong className={`text-lg font-bold block mt-1 ${strategyData.price_change >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {strategyData.price_change >= 0 ? "+" : ""}{formatCurrency(strategyData.price_change)} ({strategyData.price_change_percent >= 0 ? "+" : ""}{strategyData.price_change_percent.toFixed(1)}%)
                    </strong>
                  </div>
                </div>
              </section>

              {/* WHY THIS STRATEGY */}
              <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white">WHY THIS RECOMMENDATION?</h3>
                  <p className="text-xs text-slate-400 mt-1">Factors utilized by the decision engine to formulate this pricing target.</p>
                </div>
                <ul className="space-y-3">
                  {strategyData.reasons && strategyData.reasons.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-semibold">
                      <span className="text-violet-500 mt-1.5">•</span>
                      <span>{reason}</span>
                    </li>
                  ))}
                  {(!strategyData.reasons || strategyData.reasons.length === 0) && (
                    <li className="text-slate-500 italic text-sm">Data unavailable</li>
                  )}
                </ul>
              </section>
            </div>

            {/* Right: Recommended Action & Explanations */}
            <div className="space-y-6">
              <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6 text-left">
                <div>
                  <span className="text-[10px] font-bold tracking-wider uppercase bg-violet-50 dark:bg-violet-950/20 text-violet-600 dark:text-violet-400 px-2.5 py-1 rounded-full">RECOMMENDED ACTION</span>
                  <h3 className="text-base font-bold mt-4 leading-relaxed text-slate-900 dark:text-white">{strategyData.recommended_action}</h3>
                </div>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="block text-slate-400 font-medium">Monitoring Priority</span>
                    <span className="block font-bold text-slate-900 dark:text-white text-sm mt-1 uppercase tracking-wider">{strategyData.monitoring_priority}</span>
                  </div>
                  <div>
                    <span className="block text-slate-400 font-medium">Recommended Review</span>
                    <span className="block font-bold text-slate-900 dark:text-white text-sm mt-1">
                      {strategyData.review_period_days ? `After ${strategyData.review_period_days} days` : "After next cycle"}
                    </span>
                  </div>
                </div>
              </section>

              <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white">STRATEGY EXPLANATION</h3>
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-350 leading-relaxed font-semibold">
                  {strategyData.reasons && strategyData.reasons.length > 0 ? (
                    `Price is configured under strategy "${strategyData.strategy}" due to inventory showing ${strategyData.inventory_metrics?.status || "stable"} levels, competitor market position, and demand forecast directions. ${strategyData.recommended_action}`
                  ) : (
                    "No pricing signals could be calculated from current database inputs."
                  )}
                </p>
              </section>
            </div>
          </div>

          {/* PRICE IMPACT ANALYSIS */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
            <div className="border-b border-slate-100 dark:border-slate-800 pb-4">
              <h3 className="text-base font-extrabold text-slate-900 dark:text-white">PRICE IMPACT ANALYSIS</h3>
              <p className="text-xs text-slate-400 mt-1">Comparison between baseline actual parameters and estimated demand elasticities under optimized prices.</p>
            </div>

            {strategyData.expected_impact?.available ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Current Price</span>
                  <strong className="block text-sm font-bold text-slate-700 dark:text-slate-300 mt-1.5">{formatCurrency(strategyData.current_price)}</strong>
                  <span className="inline-block text-[9px] bg-slate-150 text-slate-650 dark:bg-slate-800 dark:text-slate-400 px-1.5 py-0.5 rounded mt-2">Actual</span>
                </article>
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Recommended Price</span>
                  <strong className="block text-sm font-bold text-slate-900 dark:text-white mt-1.5">{formatCurrency(strategyData.recommended_price)}</strong>
                  <span className="inline-block text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-950/20 dark:text-violet-400 px-1.5 py-0.5 rounded mt-2">Forecast</span>
                </article>
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Price Change %</span>
                  <strong className={`block text-sm font-bold mt-1.5 ${strategyData.price_change_percent >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                    {strategyData.price_change_percent >= 0 ? "+" : ""}{strategyData.price_change_percent.toFixed(1)}%
                  </strong>
                  <span className="inline-block text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-950/20 dark:text-violet-400 px-1.5 py-0.5 rounded mt-2">Forecast</span>
                </article>
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Expected Revenue</span>
                  <strong className="block text-sm font-bold text-slate-900 dark:text-white mt-1.5">{formatCurrency(strategyData.expected_impact.expected_revenue)}</strong>
                  <span className="inline-block text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-950/20 dark:text-violet-400 px-1.5 py-0.5 rounded mt-2">Forecast</span>
                </article>
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Expected Profit</span>
                  <strong className="block text-sm font-bold text-slate-900 dark:text-white mt-1.5">{formatCurrency(strategyData.expected_impact.expected_profit)}</strong>
                  <span className="inline-block text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-950/20 dark:text-violet-400 px-1.5 py-0.5 rounded mt-2">Forecast</span>
                </article>
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Expected Margin</span>
                  <strong className="block text-sm font-bold text-slate-900 dark:text-white mt-1.5">{strategyData.expected_impact.expected_margin}%</strong>
                  <span className="inline-block text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-950/20 dark:text-violet-400 px-1.5 py-0.5 rounded mt-2">Forecast</span>
                </article>
                <article className="p-4 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">Expected Units Sold</span>
                  <strong className="block text-sm font-bold text-slate-900 dark:text-white mt-1.5">{strategyData.expected_impact.expected_units_sold} units</strong>
                  <span className="inline-block text-[9px] bg-violet-100 text-violet-700 dark:bg-violet-950/20 dark:text-violet-400 px-1.5 py-0.5 rounded mt-2">Forecast</span>
                </article>
              </div>
            ) : (
              <div className="bg-slate-50 dark:bg-slate-950/40 p-6 text-center rounded-xl text-slate-500 italic">
                Insufficient data
              </div>
            )}
          </section>

          {/* Bottom Grid: Market Position, Demand & Inventory */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* MARKET POSITION */}
            <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-extrabold text-slate-900 dark:text-white">MARKET POSITION</h3>
                <p className="text-xs text-slate-400 mt-1">Comparison metrics calculated from active competitor scans.</p>
              </div>

              {strategyData.competitor_metrics?.available ? (
                <div className="relative border border-slate-150 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-50/20">
                  <table className="w-full text-xs text-left text-slate-700 dark:text-slate-300">
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 bg-white dark:bg-slate-900 text-slate-750 dark:text-slate-350">
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Our Current Price</td>
                        <td className="px-4 py-2.5 font-semibold text-right">{formatCurrency(strategyData.current_price)}</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Market Average</td>
                        <td className="px-4 py-2.5 font-semibold text-right">{formatCurrency(strategyData.competitor_metrics.average_competitor_price)}</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Market Median</td>
                        <td className="px-4 py-2.5 font-semibold text-right">{formatCurrency(strategyData.competitor_metrics.median_competitor_price)}</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Lowest Competitor</td>
                        <td className="px-4 py-2.5 font-semibold text-right">{formatCurrency(strategyData.competitor_metrics.lowest_competitor_price)}</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Highest Competitor</td>
                        <td className="px-4 py-2.5 font-semibold text-right">{formatCurrency(strategyData.competitor_metrics.highest_competitor_price)}</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Price Gap</td>
                        <td className={`px-4 py-2.5 font-semibold text-right ${(strategyData.competitor_metrics.price_gap || 0) <= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                          {(strategyData.competitor_metrics.price_gap || 0) <= 0 ? "" : "+"}{formatCurrency(strategyData.competitor_metrics.price_gap)} ({(strategyData.competitor_metrics.price_gap_percent || 0).toFixed(1)}%)
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Competitive Pressure</td>
                        <td className="px-4 py-2.5 font-semibold text-right">
                          <span className={`inline-block px-2 py-0.5 rounded font-bold ${strategyData.competitor_metrics.competitive_pressure > 50 ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"}`}>
                            {strategyData.competitor_metrics.competitive_pressure.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Market Position</td>
                        <td className="px-4 py-2.5 font-semibold text-right capitalize">{strategyData.competitor_metrics.market_position.replace("_", " ")}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="bg-slate-50 dark:bg-slate-950/40 p-10 text-center rounded-xl text-slate-500 italic text-xs">
                  No competitor pricing data available.
                </div>
              )}
            </section>

            {/* DEMAND & INVENTORY SIGNALS */}
            <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-extrabold text-slate-900 dark:text-white">DEMAND & INVENTORY SIGNALS</h3>
                <p className="text-xs text-slate-400 mt-1">Dynamic parameters computed from Prophet forecasts and transactional histories.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <article className="p-4 bg-slate-50/50 dark:bg-slate-950/20 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Demand Trend</span>
                  <div className="flex items-center gap-2 mt-2">
                    <strong className="text-sm font-bold text-slate-800 dark:text-white">{strategyData.demand_metrics?.forecast_direction || "Stable"}</strong>
                    <span className="text-base font-bold">
                      {strategyData.demand_metrics?.forecast_direction === "Increasing" ? "↑" : strategyData.demand_metrics?.forecast_direction === "Decreasing" ? "↓" : "→"}
                    </span>
                  </div>
                </article>

                <article className="p-4 bg-slate-50/50 dark:bg-slate-950/20 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Forecast Direction</span>
                  <div className="flex items-center gap-2 mt-2">
                    <strong className="text-sm font-bold text-slate-800 dark:text-white">{strategyData.demand_metrics?.forecast_direction || "Stable"}</strong>
                    <span className="text-base font-bold">
                      {strategyData.demand_metrics?.forecast_direction === "Increasing" ? "↑" : strategyData.demand_metrics?.forecast_direction === "Decreasing" ? "↓" : "→"}
                    </span>
                  </div>
                </article>

                <article className="p-4 bg-slate-50/50 dark:bg-slate-950/20 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Current Stock</span>
                  <strong className="text-sm font-bold text-slate-800 dark:text-white block mt-2">{strategyData.inventory_metrics?.current_stock || 0} units</strong>
                </article>

                <article className="p-4 bg-slate-50/50 dark:bg-slate-950/20 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Days of Supply</span>
                  <strong className={`text-sm font-bold block mt-2 ${typeof strategyData.inventory_metrics?.days_of_supply === 'number' && strategyData.inventory_metrics.days_of_supply < 10 ? "text-rose-600" : "text-slate-800 dark:text-white"}`}>
                    {typeof strategyData.inventory_metrics?.days_of_supply === 'number' ? `${strategyData.inventory_metrics.days_of_supply} days` : strategyData.inventory_metrics?.days_of_supply || "Data unavailable"}
                  </strong>
                </article>

                <article className="p-4 bg-slate-50/50 dark:bg-slate-950/20 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Seasonal Status</span>
                  <strong className="text-sm font-bold text-slate-800 dark:text-white block mt-2">{strategyData.seasonal_metrics?.seasonal_status || "Stable"}</strong>
                </article>

                <article className="p-4 bg-slate-50/50 dark:bg-slate-950/20 rounded-xl border border-slate-100 dark:border-slate-850">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Units Sold (30D)</span>
                  <strong className="text-sm font-bold text-slate-800 dark:text-white block mt-2">{strategyData.inventory_metrics?.available ? `${(strategyData.inventory_metrics.daily_sales_velocity * 30).toFixed(0)} units` : "Insufficient data"}</strong>
                </article>
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
