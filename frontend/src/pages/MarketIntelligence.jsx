import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  AreaChart,
  Area,
} from "recharts";

export default function MarketIntelligence({
  products,
  token,
  API,
  showToast,
  formatCurrency,
}) {
  const [portfolio, setPortfolio] = useState(null);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [productStats, setProductStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingPortfolio, setLoadingPortfolio] = useState(false);
  const [errorPortfolio, setErrorPortfolio] = useState(null);
  const [errorProduct, setErrorProduct] = useState(null);

  // Set default product
  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      setSelectedProductId(products[0].id);
    }
  }, [products, selectedProductId]);

  // Load portfolio analytics
  const fetchPortfolio = async () => {
    setLoadingPortfolio(true);
    setErrorPortfolio(null);
    try {
      const response = await axios.get(`${API}/api/market-intelligence/portfolio`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 10000
      });
      setPortfolio(response.data);
    } catch (err) {
      console.error("Error loading portfolio metrics:", err);
      setErrorPortfolio(err.message || "Failed to load portfolio market intelligence summary.");
      showToast("Failed to load portfolio market intelligence summary.", "error");
    } finally {
      setLoadingPortfolio(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, [token, API]);

  // Load single product intelligence
  useEffect(() => {
    if (!selectedProductId) return;

    const fetchProductStats = async () => {
      setLoading(true);
      setErrorProduct(null);
      try {
        const response = await axios.get(`${API}/api/market-intelligence/${selectedProductId}`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 10000
        });
        setProductStats(response.data);
      } catch (err) {
        console.error("Error loading product intelligence stats:", err);
        setErrorProduct(err.message || "Failed to load product intelligence details.");
        showToast("Failed to load product intelligence details.", "error");
      } finally {
        setLoading(false);
      }
    };

    fetchProductStats();
  }, [selectedProductId, token, API]);

  // Map Price Index Chart Data
  const getPriceIndexData = () => {
    if (!productStats) return [];
    const mm = productStats.market_metrics;
    
    // If no competitors, return empty comparison
    if (mm.competitor_count === 0) {
      return [
        { name: "Our Price", price: productStats.our_price, isOurs: true }
      ];
    }

    return [
      { name: "Min Price", price: mm.market_min_price, isOurs: false },
      { name: "Our Price", price: productStats.our_price, isOurs: true },
      { name: "Average", price: mm.market_average_price, isOurs: false },
      { name: "Median", price: mm.market_median_price, isOurs: false },
      { name: "Max Price", price: mm.market_max_price, isOurs: false }
    ];
  };

  // Map Forecast Chart Data
  const getForecastChartData = () => {
    if (!productStats) return [];
    const dm = productStats.demand_metrics;
    return [
      { name: "Short Term (30d)", demand: dm.short_term_forecast },
      { name: "Mid Term (90d)", demand: dm.mid_term_forecast },
      { name: "Long Term (365d)", demand: dm.long_term_forecast }
    ];
  };

  // Map Seasonal breakdown Chart Data
  const getSeasonalBreakdownData = () => {
    if (!productStats || !productStats.seasonal_metrics?.seasonal_breakdown) return [];
    return productStats.seasonal_metrics.seasonal_breakdown.map((row) => ({
      month: (row.period || row.month_name || "").substring(0, 3),
      demand: row.average_demand
    }));
  };

  // Helpers for filtering portfolio summaries
  const getOpportunitiesList = () => {
    if (!portfolio?.portfolio) return [];
    return portfolio.portfolio.filter((p) =>
      ["Market Opportunity", "High Demand Opportunity"].includes(p.classification)
    );
  };

  const getThreatsList = () => {
    if (!portfolio?.portfolio) return [];
    return portfolio.portfolio.filter((p) => p.classification === "Competitive Threat");
  };

  const priceIndexData = getPriceIndexData();
  const forecastData = getForecastChartData();
  const seasonalData = getSeasonalBreakdownData();
  const opportunities = getOpportunitiesList();
  const threats = getThreatsList();

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <header className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-bold text-violet-600 dark:text-violet-400 uppercase tracking-widest block mb-1">
            Intelligence
          </p>
          <h1 className="text-2xl font-black text-slate-800 dark:text-white leading-tight">
            Market Intelligence Engine
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Cross-functional analysis synthesizing competitor monitoring, demand forecasting, seasonal patterns, and stock risks.
          </p>
        </div>
      </header>

      {errorPortfolio && (
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800 p-4 rounded-2xl text-left text-xs font-semibold text-rose-600 dark:text-rose-400">
          Failed to load portfolio market intelligence. Error: {errorPortfolio}
        </div>
      )}

      {/* 1. Market Overview Portfolio Dashboard */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total opportunities count */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Market Opportunities</span>
          {loadingPortfolio ? (
            <div className="h-8 w-12 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong className="text-3xl font-black text-emerald-500 block mt-1">
              {(portfolio?.classification_counts?.["Market Opportunity"] ?? 0) +
                (portfolio?.classification_counts?.["High Demand Opportunity"] ?? 0)}
            </strong>
          )}
          <span className="text-[10px] text-slate-400 block mt-1">High demand or low competitor pressure items</span>
        </div>

        {/* Competitive threats count */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Active Competitive Threats</span>
          {loadingPortfolio ? (
            <div className="h-8 w-12 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong className="text-3xl font-black text-rose-500 block mt-1">
              {portfolio?.classification_counts?.["Competitive Threat"] ?? 0}
            </strong>
          )}
          <span className="text-[10px] text-slate-400 block mt-1">Over 50% competitors undercutting us</span>
        </div>

        {/* Inventory risks count */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Critical Inventory Risks</span>
          {loadingPortfolio ? (
            <div className="h-8 w-12 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong className="text-3xl font-black text-amber-500 block mt-1">
              {(portfolio?.classification_counts?.["Stockout Risk"] ?? 0) +
                (portfolio?.classification_counts?.["Overstock Risk"] ?? 0)}
            </strong>
          )}
          <span className="text-[10px] text-slate-400 block mt-1">Stockout under 10 days or overstock over 45 days</span>
        </div>

        {/* Average market pressure */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Average Pricing Pressure</span>
          {loadingPortfolio ? (
            <div className="h-8 w-12 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong className="text-3xl font-black text-slate-800 dark:text-slate-100 block mt-1">
              {portfolio?.average_market_pressure?.toFixed(1) ?? "0.0"}%
            </strong>
          )}
          <span className="text-[10px] text-slate-400 block mt-1">Overall percentage of cheaper competitor listings</span>
        </div>
      </section>

      {/* Selectors Filter Block */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Product selector */}
        <div className="space-y-1 text-left">
          <label htmlFor="intel-prod-select" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Analysis Product SKU
          </label>
          <select
            id="intel-prod-select"
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          >
            {products && products.length > 0 ? (
              products.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))
            ) : (
              <option value="">No products loaded</option>
            )}
          </select>
        </div>

        {/* Start Date */}
        <div className="space-y-1 text-left">
          <label htmlFor="intel-start-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Start Date
          </label>
          <input
            id="intel-start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>

        {/* End Date */}
        <div className="space-y-1 text-left">
          <label htmlFor="intel-end-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            End Date
          </label>
          <input
            id="intel-end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>
      </section>

      {errorProduct && (
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800 p-4 rounded-2xl text-left text-xs font-semibold text-rose-600 dark:text-rose-400">
          Failed to load product intelligence details. Error: {errorProduct}
        </div>
      )}

      {/* Loading indicator */}
      {loading && (
        <div className="flex items-center justify-center p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
          <span className="text-xs font-semibold text-slate-500 ml-3">Synthesizing intelligence telemetry metrics...</span>
        </div>
      )}

      {/* Product Specific Intelligence Summary */}
      {!loading && productStats && (
        <div className="space-y-6">
          {/* Metrics summary cards */}
          <section className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Status Classification */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Classification</span>
              <strong className={`text-sm font-black block mt-2 px-2.5 py-1 rounded-lg text-center uppercase tracking-wide ${
                productStats.classification === "Stockout Risk" ? "bg-rose-50 text-rose-600 dark:bg-rose-950/20 dark:text-rose-400" :
                productStats.classification === "Overstock Risk" ? "bg-amber-50 text-amber-600 dark:bg-amber-950/20 dark:text-amber-400" :
                productStats.classification === "High Demand Opportunity" ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/20 dark:text-emerald-400" :
                productStats.classification === "Market Opportunity" ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/20 dark:text-indigo-400" :
                productStats.classification === "Competitive Threat" ? "bg-rose-50 text-rose-600 dark:bg-rose-950/20 dark:text-rose-400" :
                "bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
              }`}>
                {productStats.classification}
              </strong>
            </div>

            {/* Pricing Position */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Pricing Position</span>
              <strong className="text-lg font-black text-slate-800 dark:text-slate-100 block mt-2 uppercase tracking-tight">
                {productStats.market_metrics.competitor_count > 0 
                  ? productStats.competitive_metrics.pricing_position.replace("_", " ") 
                  : "No competitor data"}
              </strong>
            </div>

            {/* Competitive pressure */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Competitive Pressure</span>
              <strong className="text-xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                {productStats.market_metrics.competitor_count > 0 
                  ? `${productStats.competitive_metrics.competitive_pressure_score.toFixed(1)}%` 
                  : "No competitor data"}
              </strong>
              {productStats.market_metrics.competitor_count > 0 && (
                <div className="mt-2.5 h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${
                      productStats.competitive_metrics.competitive_pressure_score > 50 ? "bg-rose-500" : "bg-emerald-500"
                    }`} 
                    style={{ width: `${productStats.competitive_metrics.competitive_pressure_score}%` }}
                  ></div>
                </div>
              )}
            </div>

            {/* Price Volatility */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Price Volatility</span>
              <strong className="text-xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                {productStats.market_metrics.competitor_count > 0 
                  ? formatCurrency(productStats.market_metrics.competitor_price_volatility) 
                  : "No competitor data"}
              </strong>
              <span className="text-[10px] text-slate-400 block mt-1">Standard deviation of competitor prices</span>
            </div>

            {/* Days of Supply */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Days of Supply</span>
              <strong className={`text-xl font-black block mt-1 ${
                productStats.inventory_metrics.stockout_risk ? "text-rose-500" : "text-slate-800 dark:text-slate-100"
              }`}>
                {productStats.inventory_metrics.days_of_supply.toFixed(1)} Days
              </strong>
              <span className="text-[10px] text-slate-400 block mt-1">Current Stock: {productStats.inventory_metrics.current_inventory}</span>
            </div>
          </section>

          {/* Dynamic insights section */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
              Telemetry Insights & Signals
            </h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {productStats.insights.map((ins, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <span className="text-violet-500 mt-0.5">&bull;</span>
                  <span>{ins}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Grid visual charts */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Price Index comparison */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Market Price Index
              </h3>
              <div className="h-64">
                {productStats.market_metrics.competitor_count > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={priceIndexData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis 
                        dataKey="name" 
                        tick={{ fill: "#64748B", fontSize: 9, fontWeight: "bold" }}
                        axisLine={{ stroke: "#CBD5E1" }} 
                      />
                      <YAxis 
                        tick={{ fill: "#64748B", fontSize: 9 }}
                        axisLine={{ stroke: "#CBD5E1" }} 
                      />
                      <ChartTooltip 
                        formatter={(value) => [formatCurrency(value), "Price"]}
                        contentStyle={{ background: "#1E293B", color: "#fff", borderRadius: "12px", border: "none", fontSize: "11px" }}
                      />
                      <Bar dataKey="price" radius={[8, 8, 0, 0]}>
                        {priceIndexData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.isOurs ? "#8B5CF6" : "#94A3B8"} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-400">No competitor prices observed for this item.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Demand forecast chart */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Demand Projections & Forecast Trend
              </h3>
              <div className="h-64">
                {productStats.demand_metrics.short_term_forecast > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={forecastData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <defs>
                        <linearGradient id="colorDemand" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis 
                        dataKey="name" 
                        tick={{ fill: "#64748B", fontSize: 9 }}
                        axisLine={{ stroke: "#CBD5E1" }}
                      />
                      <YAxis 
                        tick={{ fill: "#64748B", fontSize: 9 }}
                        axisLine={{ stroke: "#CBD5E1" }}
                      />
                      <ChartTooltip 
                        formatter={(value) => [Math.round(value), "Expected Demand"]}
                        contentStyle={{ background: "#1E293B", color: "#fff", borderRadius: "12px", border: "none", fontSize: "11px" }}
                      />
                      <Area 
                        name="Projected Quantity" 
                        type="monotone" 
                        dataKey="demand" 
                        stroke="#8B5CF6" 
                        fillOpacity={1} 
                        fill="url(#colorDemand)" 
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-400">Insufficient sales history to render forecasting predictions.</span>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Seasonal Pattern Chart */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Seasonal Patterns & Indices Breakdown
              </h3>
              <div className="h-64">
                {seasonalData && seasonalData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={seasonalData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis 
                        dataKey="month" 
                        tick={{ fill: "#64748B", fontSize: 9 }}
                        axisLine={{ stroke: "#CBD5E1" }}
                      />
                      <YAxis 
                        tick={{ fill: "#64748B", fontSize: 9 }}
                        axisLine={{ stroke: "#CBD5E1" }}
                      />
                      <ChartTooltip 
                        formatter={(value) => [value.toFixed(1), "Average Demand Index"]}
                        contentStyle={{ background: "#1E293B", color: "#fff", borderRadius: "12px", border: "none", fontSize: "11px" }}
                      />
                      <Line 
                        name="Seasonal Index" 
                        type="monotone" 
                        dataKey="demand" 
                        stroke="#10B981" 
                        strokeWidth={2.5} 
                        dot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-400">No seasonal breakdown data loaded for this item.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Seasonal context summary card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                  Seasonal Indicators
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Current Season Status</span>
                    <strong className={`text-xs font-bold block mt-1 uppercase ${
                      productStats.seasonal_metrics?.current_season === "peak" ? "text-emerald-500" :
                      productStats.seasonal_metrics?.current_season === "low" ? "text-rose-500" :
                      "text-slate-600 dark:text-slate-400"
                    }`}>
                      {productStats.seasonal_metrics?.current_season || "N/A"}
                    </strong>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Peak Period month</span>
                    <strong className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-1">
                      {productStats.seasonal_metrics?.peak_period || "N/A"}
                    </strong>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Off-Season month</span>
                    <strong className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-1">
                      {productStats.seasonal_metrics?.low_period || "N/A"}
                    </strong>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Seasonal Strength Ratio</span>
                    <strong className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-1">
                      {(productStats.seasonal_metrics?.seasonal_strength ?? 0).toFixed(2)}x
                    </strong>
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-100 dark:border-slate-800 pt-4 mt-4 text-[11px] text-slate-400 font-semibold">
                * Strength represents Peak-to-Low ratio vs historical baseline sales.
              </div>
            </div>
          </section>

          {/* Opportunities and threats columns list */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Opportunities */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-3">
                Detected Portfolio Market Opportunities
              </h3>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {opportunities.length > 0 ? (
                  opportunities.map((p, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                      <div>
                        <strong className="text-xs font-bold text-slate-800 dark:text-white block">{p.product_name}</strong>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wide block">{p.classification}</span>
                      </div>
                      <strong className="text-xs text-slate-700 dark:text-slate-300">{formatCurrency(p.our_price)}</strong>
                    </div>
                  ))
                ) : (
                  <span className="text-xs text-slate-400 block p-4 text-center">No opportunities registered.</span>
                )}
              </div>
            </div>

            {/* Threats */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-3">
                Detected Portfolio Competitive Threats
              </h3>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {threats.length > 0 ? (
                  threats.map((p, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                      <div>
                        <strong className="text-xs font-bold text-slate-800 dark:text-white block">{p.product_name}</strong>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wide block">{p.classification}</span>
                      </div>
                      <strong className="text-xs text-slate-700 dark:text-slate-300">{formatCurrency(p.our_price)}</strong>
                    </div>
                  ))
                ) : (
                  <span className="text-xs text-slate-400 block p-4 text-center">No critical competitive threats registered.</span>
                )}
              </div>
            </div>
          </section>

          {/* Product intelligence datagrid table */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left">
            <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
              Catalog Intelligence Summary Matrix
            </h3>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="pb-3 pr-4">Product Name</th>
                    <th className="pb-3 pr-4">Our Price</th>
                    <th className="pb-3 pr-4">Market Avg</th>
                    <th className="pb-3 pr-4">Pricing Pressure</th>
                    <th className="pb-3 pr-4">Supply Level</th>
                    <th className="pb-3 pr-4">Classification status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {portfolio?.portfolio && portfolio.portfolio.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition duration-150">
                      <td className="py-3 pr-4 font-bold text-slate-800 dark:text-slate-200">
                        {item.product_name}
                      </td>
                      <td className="py-3 pr-4 font-black">
                        {formatCurrency(item.our_price)}
                      </td>
                      <td className="py-3 pr-4 font-semibold text-slate-500 dark:text-slate-400">
                        {item.market_metrics.competitor_count > 0 
                          ? formatCurrency(item.market_metrics.market_average_price) 
                          : "No competitor data"}
                      </td>
                      <td className="py-3 pr-4">
                        {item.market_metrics.competitor_count > 0 ? (
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            item.competitive_metrics.competitive_pressure_score > 50 
                              ? "bg-rose-50 text-rose-600 dark:bg-rose-950/30 dark:text-rose-400" 
                              : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400"
                          }`}>
                            {item.competitive_metrics.competitive_pressure_score.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-slate-400">No competitor data</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                        {item.inventory_metrics.days_of_supply.toFixed(1)} Days ({item.inventory_metrics.current_inventory} units)
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          item.classification === "Stockout Risk" ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400" :
                          item.classification === "Overstock Risk" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                          item.classification === "High Demand Opportunity" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
                          "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400"
                        }`}>
                          {item.classification}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
