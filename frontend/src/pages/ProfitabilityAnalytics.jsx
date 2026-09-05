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

export default function ProfitabilityAnalytics({
  products,
  token,
  API,
  showToast,
  formatCurrency,
}) {
  const [selectedProductId, setSelectedProductId] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  const [overview, setOverview] = useState(null);
  const [topProducts, setTopProducts] = useState(null);
  const [singleProductStats, setSingleProductStats] = useState(null);
  const [trends, setTrends] = useState([]);
  
  const [loadingStatic, setLoadingStatic] = useState(false);
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [error, setError] = useState(null);

  const loading = loadingStatic || loadingOverview;

  // Fetch static portfolio metrics once on mount
  useEffect(() => {
    const fetchStaticData = async () => {
      setLoadingStatic(true);
      setError(null);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        
        // Fetch Top Products & catalog tables
        const topRes = await axios.get(`${API}/api/profitability/top-products`, { 
          headers,
          timeout: 10000 
        });
        setTopProducts(topRes.data);
   
        // Fetch aggregated trends for charts
        const trendsRes = await axios.get(`${API}/api/profitability/trends`, { 
          headers,
          timeout: 10000 
        });
        setTrends(trendsRes.data);
      } catch (err) {
        console.error("Error loading profitability static metrics:", err);
        setError(err.message || "Failed to load static profitability metrics.");
        showToast("Failed to load static profitability metrics.", "error");
      } finally {
        setLoadingStatic(false);
      }
    };
    fetchStaticData();
  }, [token, API]);

  // Fetch overview/details whenever selectedProductId changes
  useEffect(() => {
    const fetchOverviewData = async () => {
      setLoadingOverview(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        
        // Fetch High-level Overview
        const overviewRes = await axios.get(`${API}/api/profitability/overview`, {
          headers,
          params: { product_id: selectedProductId !== "all" ? selectedProductId : undefined },
          timeout: 10000
        });
        setOverview(overviewRes.data);
   
        // Fetch details if single product is selected
        if (selectedProductId !== "all") {
          const detailRes = await axios.get(`${API}/api/profitability/product/${selectedProductId}`, { 
            headers,
            timeout: 10000 
          });
          setSingleProductStats(detailRes.data);
        } else {
          setSingleProductStats(null);
        }
      } catch (err) {
        console.error("Error loading profitability overview details:", err);
        showToast("Failed to load profitability details.", "error");
      } finally {
        setLoadingOverview(false);
      }
    };
    fetchOverviewData();
  }, [selectedProductId, token, API]);

  // Export report to CSV
  const handleExportCSV = () => {
    if (!topProducts?.all_products) {
      showToast("No product data loaded to export.", "error");
      return;
    }

    const headers = ["Product ID", "Product Name", "Units Sold", "Revenue", "Cost", "Profit", "Margin %"];
    const rows = topProducts.all_products.map((p) => [
      p.product_id,
      `"${p.product_name}"`,
      p.units_sold,
      p.revenue,
      p.cost_data_available ? p.total_cost : "N/A",
      p.cost_data_available ? p.gross_profit : "N/A",
      p.cost_data_available ? p.gross_margin_percent?.toFixed(1) : "N/A",
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `profitability_analytics_report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV report exported successfully.", "success");
  };

  // Process data for Actual vs Forecast Revenue Chart
  const getActualVsForecastData = () => {
    if (selectedProductId === "all") {
      // Portfolio actual vs portfolio projected sum
      if (!topProducts?.all_products) return [];
      const actualSum = topProducts.all_products.reduce((acc, p) => acc + p.revenue, 0);
      const projectedSum = topProducts.all_products.reduce((acc, p) => acc + (p.forecast_metrics?.projected_revenue || 0), 0);
      return [
        { name: "Actual Revenue", amount: actualSum, type: "Actual" },
        { name: "Projected Revenue (Forecast)", amount: projectedSum, type: "Forecast / Estimated" }
      ];
    } else {
      if (!singleProductStats) return [];
      return [
        { name: "Actual Revenue", amount: singleProductStats.revenue, type: "Actual" },
        { name: "Projected Revenue (Forecast)", amount: singleProductStats.forecast_metrics.projected_revenue, type: "Forecast / Estimated" }
      ];
    }
  };

  // Process trends data for single product vs entire portfolio
  const getTrendsData = () => {
    if (selectedProductId === "all") {
      return trends;
    } else {
      return singleProductStats?.monthly_trends || [];
    }
  };

  const actualVsForecastData = getActualVsForecastData();
  const activeTrends = getTrendsData();

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold text-violet-600 dark:text-violet-400 uppercase tracking-widest block mb-1">
            Financials
          </p>
          <h1 className="text-2xl font-black text-slate-800 dark:text-white leading-tight">
            Profitability Analytics Dashboard
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time tracking of revenue streams, profit margins, cost indicators, and pricing impact estimates.
          </p>
        </div>

        <button
          onClick={handleExportCSV}
          disabled={loading || !topProducts}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-800 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition duration-150 shadow-sm"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          <span>Export CSV Report</span>
        </button>
      </header>

      {/* Selectors Panel */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Product selector */}
        <div className="space-y-1 text-left">
          <label htmlFor="profit-prod-select" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Selected Product SKU
          </label>
          <select
            id="profit-prod-select"
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          >
            <option value="all">All Products (Portfolio)</option>
            {products && products.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        {/* Start Date */}
        <div className="space-y-1 text-left">
          <label htmlFor="profit-start-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Start Date
          </label>
          <input
            id="profit-start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>

        {/* End Date */}
        <div className="space-y-1 text-left">
          <label htmlFor="profit-end-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            End Date
          </label>
          <input
            id="profit-end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>
      </section>

      {error && (
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800 p-4 rounded-2xl text-left text-xs font-semibold text-rose-600 dark:text-rose-400">
          Failed to load profitability analytics. Error: {error}
        </div>
      )}

      {!loading && !overview && !error && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-8 rounded-2xl shadow-sm text-center">
          <span className="text-xs font-semibold text-slate-500">No product profitability records found.</span>
        </div>
      )}

      {/* Loading state indicator */}
      {loading && (
        <div className="flex items-center justify-center p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
          <span className="text-xs font-semibold text-slate-500 ml-3">Calculating profitability metrics...</span>
        </div>
      )}

      {/* Overview Analytics Dashboard */}
      {!loading && overview && (
        <div className="space-y-6">
          {/* KPI Cards Grid */}
          <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* 1. Revenue KPI */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Revenue</span>
              <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                {formatCurrency(overview.total_revenue)}
              </strong>
              <span className="text-[10px] text-emerald-500 font-bold block mt-2">
                +{overview.revenue_growth.toFixed(1)}% Growth
              </span>
            </div>

            {/* 2. Gross Profit KPI */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Gross Profit</span>
              {overview.cost_data_available ? (
                <>
                  <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                    {formatCurrency(overview.gross_profit)}
                  </strong>
                  <span className="text-[10px] text-emerald-500 font-bold block mt-2">
                    +{overview.profit_growth?.toFixed(1)}% Growth
                  </span>
                </>
              ) : (
                <>
                  <strong className="text-lg font-black text-rose-500 block mt-2">
                    Cost data unavailable
                  </strong>
                  <span className="text-[10px] text-slate-400 block mt-2">Cost price missing on item catalog</span>
                </>
              )}
            </div>

            {/* 3. Gross Margin KPI */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Gross Margin</span>
              {overview.cost_data_available ? (
                <>
                  <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                    {overview.gross_margin_percent?.toFixed(1)}%
                  </strong>
                  <div className="mt-3.5 h-1 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-violet-500 rounded-full" 
                      style={{ width: `${overview.gross_margin_percent}%` }}
                    ></div>
                  </div>
                </>
              ) : (
                <>
                  <strong className="text-lg font-black text-rose-500 block mt-2">
                    Cost data unavailable
                  </strong>
                  <span className="text-[10px] text-slate-400 block mt-2">Margin calculation skipped</span>
                </>
              )}
            </div>

            {/* 4. Units Sold KPI */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Units Sold</span>
              <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                {overview.units_sold} Units
              </strong>
              <span className="text-[10px] text-slate-400 block mt-2">
                Avg Selling Price: {formatCurrency(overview.average_selling_price)}
              </span>
            </div>
          </section>

          {/* Time Analysis Charts section */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {/* Revenue / Profit trends lines */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Historical Financial Trend (Revenue & Profit)
              </h3>
              {activeTrends.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={activeTrends} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
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
                        formatter={(value) => [formatCurrency(value), ""]}
                        contentStyle={{ background: "#1E293B", color: "#fff", borderRadius: "12px", border: "none", fontSize: "11px" }}
                      />
                      <Legend wrapperStyle={{ fontSize: "10px", marginTop: "10px" }} />
                      <Line 
                        name="Revenue" 
                        type="monotone" 
                        dataKey="revenue" 
                        stroke="#8B5CF6" 
                        strokeWidth={2.5} 
                        dot={{ r: 3 }}
                      />
                      {overview.cost_data_available && (
                        <Line 
                           name="Gross Profit" 
                           type="monotone" 
                           dataKey="profit" 
                           stroke="#10B981" 
                           strokeWidth={2}
                           dot={{ r: 3 }}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="py-4 px-5 border border-dashed border-violet-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 rounded-xl flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-violet-100 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 mt-0.5">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 11.082 1.25c-.27.18-.39.444-.39.908V15H12m-1.5 1.5H15M9 6a.75.75 0 01.75-.75h4.5a.75.75 0 01.75.75v5.25a.75.75 0 01-.75.75h-4.5A.75.75 0 019 11.25V6z" />
                    </svg>
                  </div>
                  <div>
                    <strong className="text-xs font-bold text-slate-700 dark:text-slate-200 block">
                      Historical monthly trend data is not available for this selection.
                    </strong>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 block mt-1 leading-normal">
                      The KPI summary cards and actual vs forecast charts are still calculated and displayed using the available transaction records and model forecasts.
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Actual vs Forecast Area chart */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Revenue: Actual vs Forecast
              </h3>
              <div className="h-64">
                {actualVsForecastData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={actualVsForecastData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
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
                        formatter={(value) => [formatCurrency(value), "Amount"]}
                        contentStyle={{ background: "#1E293B", color: "#fff", borderRadius: "12px", border: "none", fontSize: "11px" }}
                      />
                      <Bar dataKey="amount" radius={[8, 8, 0, 0]}>
                        {actualVsForecastData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={index === 0 ? "#8B5CF6" : "#A78BFA"} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-400">Projected values missing.</span>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-400 block mt-2 text-center font-bold">
                * Right bar explicitly denotes: Forecast / Estimated
              </span>
            </div>
          </section>

          {/* Pricing Impact Analysis widget */}
          {selectedProductId !== "all" && singleProductStats && (
            <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left">
              <div className="flex items-center justify-between mb-4 border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">
                  Pricing Recommendation Impact Analysis
                </h3>
                <span className="px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-violet-100 text-violet-700 dark:bg-violet-950/30 dark:text-violet-400 uppercase tracking-widest">
                  Forecast / Estimated
                </span>
              </div>

              {singleProductStats.pricing_impact?.available ? (
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  {/* Prices comparison */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Target Prices</span>
                    <strong className="text-xs text-slate-500 block mt-2">Current: {formatCurrency(singleProductStats.pricing_impact.current_price)}</strong>
                    <strong className="text-sm text-violet-600 block mt-1">Recommended: {formatCurrency(singleProductStats.pricing_impact.recommended_price)}</strong>
                  </div>

                  {/* Expected Revenue current vs recommended */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Expected Revenue</span>
                    <strong className="text-xs text-slate-500 block mt-2">Current: {formatCurrency(singleProductStats.pricing_impact.current_expected_revenue)}</strong>
                    <strong className="text-sm text-slate-700 dark:text-slate-300 block mt-1">Recommended: {formatCurrency(singleProductStats.pricing_impact.recommended_expected_revenue)}</strong>
                  </div>

                  {/* Expected Profit current vs recommended */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Expected Profit</span>
                    <strong className="text-xs text-slate-500 block mt-2">Current: {formatCurrency(singleProductStats.pricing_impact.current_expected_profit)}</strong>
                    <strong className="text-sm text-slate-700 dark:text-slate-300 block mt-1">Recommended: {formatCurrency(singleProductStats.pricing_impact.recommended_expected_profit)}</strong>
                  </div>

                  {/* Profit gain/loss */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Estimated Profit Change</span>
                    <strong className={`text-xl font-black block mt-2.5 ${
                      singleProductStats.pricing_impact.estimated_profit_change >= 0 ? "text-emerald-500" : "text-rose-500"
                    }`}>
                      {singleProductStats.pricing_impact.estimated_profit_change >= 0 ? "+" : ""}{formatCurrency(singleProductStats.pricing_impact.estimated_profit_change)}
                    </strong>
                  </div>

                  {/* Margin gain/loss */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Estimated Margin Change</span>
                    <strong className={`text-xl font-black block mt-2.5 ${
                      singleProductStats.pricing_impact.estimated_margin_change >= 0 ? "text-emerald-500" : "text-rose-500"
                    }`}>
                      {singleProductStats.pricing_impact.estimated_margin_change >= 0 ? "+" : ""}{singleProductStats.pricing_impact.estimated_margin_change.toFixed(1)}%
                    </strong>
                  </div>
                </div>
              ) : (
                <div className="p-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-center">
                  <span className="text-xs text-rose-500 font-bold block">
                    Pricing impact analysis requires product cost configuration. Cost data unavailable.
                  </span>
                </div>
              )}
            </section>
          )}

          {/* Top products and low margin catalog blocks */}
          {topProducts && (
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Top performing profitable/revenue products */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-3">
                  {overview.cost_data_available ? "Top 5 Profitable Products" : "Top 5 Products by Revenue"}
                </h3>
                <div className="space-y-2">
                  {topProducts.top_profitable && topProducts.top_profitable.map((p, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                      <div>
                        <strong className="text-xs font-bold text-slate-800 dark:text-white block">{p.product_name}</strong>
                        <span className="text-[10px] text-slate-400 block">{p.units_sold} units sold</span>
                      </div>
                      <strong className="text-xs text-slate-700 dark:text-slate-300">
                        {overview.cost_data_available ? formatCurrency(p.gross_profit) : formatCurrency(p.revenue)}
                      </strong>
                    </div>
                  ))}
                </div>
              </div>

              {/* Low margin items list */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-3">
                  Low-Margin Catalog Warning
                </h3>
                <div className="space-y-2">
                  {overview.cost_data_available ? (
                    topProducts.low_margin && topProducts.low_margin.length > 0 ? (
                      topProducts.low_margin.map((p, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                          <div>
                            <strong className="text-xs font-bold text-slate-800 dark:text-white block">{p.product_name}</strong>
                            <span className="text-[10px] text-slate-400 block">{p.units_sold} units sold</span>
                          </div>
                          <strong className="text-xs text-rose-500 font-bold">
                            {p.gross_margin_percent?.toFixed(1)}% Margin
                          </strong>
                        </div>
                      ))
                    ) : (
                      <span className="text-xs text-slate-400 block p-4 text-center">All margins are healthy.</span>
                    )
                  ) : (
                    <div className="p-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-center">
                      <span className="text-xs text-rose-500 font-bold">
                        Cost data unavailable. Margin catalog warning skipped.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* Full product catalog table */}
          {topProducts && (
            <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Product Profitability Matrix
              </h3>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      <th className="pb-3 pr-4">Product Name</th>
                      <th className="pb-3 pr-4">Units Sold</th>
                      <th className="pb-3 pr-4">Revenue</th>
                      <th className="pb-3 pr-4">Total Cost</th>
                      <th className="pb-3 pr-4">Gross Profit</th>
                      <th className="pb-3 pr-4">Margin %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300">
                    {topProducts.all_products && topProducts.all_products.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition duration-150">
                        <td className="py-3 pr-4 font-bold text-slate-800 dark:text-slate-200">
                          {item.product_name}
                        </td>
                        <td className="py-3 pr-4 font-bold">
                          {item.units_sold} Units
                        </td>
                        <td className="py-3 pr-4 font-black">
                          {formatCurrency(item.revenue)}
                        </td>
                        <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                          {item.cost_data_available ? formatCurrency(item.total_cost) : "N/A"}
                        </td>
                        <td className={`py-3 pr-4 font-bold ${
                          item.cost_data_available && item.gross_profit > 0 ? "text-emerald-500" : item.cost_data_available ? "text-rose-500" : "text-slate-500"
                        }`}>
                          {item.cost_data_available ? formatCurrency(item.gross_profit) : "N/A"}
                        </td>
                        <td className={`py-3 pr-4 font-bold ${
                          item.cost_data_available && item.gross_margin_percent > 30 ? "text-emerald-500" : item.cost_data_available ? "text-rose-500" : "text-slate-500"
                        }`}>
                          {item.cost_data_available ? `${item.gross_margin_percent?.toFixed(1)}%` : "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
