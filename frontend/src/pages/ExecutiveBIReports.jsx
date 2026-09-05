import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  AreaChart,
  Area,
} from "recharts";

export default function ExecutiveBIReports({
  products,
  token,
  API,
  showToast,
  formatCurrency,
}) {
  const [selectedProductId, setSelectedProductId] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.get(`${API}/api/executive-bi/summary`, {
        headers,
        params: {
          product_id: selectedProductId !== "all" ? selectedProductId : undefined,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        },
        timeout: 15000,
      });
      setData(res.data);
    } catch (err) {
      console.error("Error fetching Executive BI Reports:", err);
      const errMsg = err.response?.data?.detail || "Failed to load Executive BI Reports summary.";
      setError(errMsg);
      showToast(errMsg, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedProductId, startDate, endDate, token, API]);

  const handleExportPDF = () => {
    window.print();
  };

  const handleExportCSV = () => {
    if (!data) {
      showToast("No report data loaded to export.", "error");
      return;
    }

    let csvRows = [];
    csvRows.push("EXECUTIVE BUSINESS INTELLIGENCE REPORT");
    csvRows.push(`Scope,${data.scope.product_name}`);
    csvRows.push(`Generated At,${new Date().toLocaleString()}`);
    csvRows.push("");

    csvRows.push("KEY PERFORMANCE INDICATORS");
    csvRows.push("Metric,Value");
    csvRows.push(`Total Revenue,${data.kpis.total_revenue}`);
    csvRows.push(`Gross Profit,${data.kpis.gross_profit}`);
    csvRows.push(`Gross Margin %,${data.kpis.gross_margin}%`);
    csvRows.push(`Units Sold,${data.kpis.units_sold}`);
    csvRows.push(`Average Selling Price,${data.kpis.average_selling_price}`);
    csvRows.push(`Revenue Growth,${data.kpis.revenue_growth}%`);
    csvRows.push("");

    csvRows.push("TOP PROFITABLE PRODUCTS");
    csvRows.push("Product ID,Product Name,Revenue,Gross Profit,Gross Margin %,Units Sold");
    data.product_performance.top_profitable.forEach((p) => {
      csvRows.push(`${p.product_id},"${p.product_name}",${p.revenue},${p.gross_profit},${p.gross_margin_percent}%,${p.units_sold}`);
    });
    csvRows.push("");

    csvRows.push("LOW MARGIN PRODUCTS");
    csvRows.push("Product ID,Product Name,Revenue,Gross Profit,Gross Margin %,Units Sold");
    data.product_performance.low_margin.forEach((p) => {
      csvRows.push(`${p.product_id},"${p.product_name}",${p.revenue},${p.gross_profit},${p.gross_margin_percent}%,${p.units_sold}`);
    });
    csvRows.push("");

    csvRows.push("CRITICAL INVENTORY RISK ITEMS");
    csvRows.push("Product ID,Product Name,Stock,Days of Supply,Demand Outlook");
    data.inventory_health.critical_inventory_risk.forEach((p) => {
      csvRows.push(`${p.product_id},"${p.product_name}",${p.stock},${p.days_of_supply},${p.demand_direction}`);
    });

    const csvContent = "data:text/csv;charset=utf-8," + csvRows.join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Executive_BI_Report_${selectedProductId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV report exported successfully.", "success");
  };

  // Pad tables to exactly 5 rows for aligned grid cards height
  const padTableData = (dataList) => {
    if (!dataList) return [];
    const result = [...dataList];
    while (result.length < 5) {
      result.push({ isPlaceholder: true });
    }
    return result;
  };

  // Prepare chart formats
  const formatChartCurrency = (value) => {
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${(value / 1000).toFixed(0)}K`;
    return `₹${value}`;
  };

  const getActualVsForecastData = () => {
    if (!data) return [];
    return [
      {
        name: "Actual Revenue",
        Amount: data.financial_performance.actual_vs_forecast.actual_revenue,
        fill: "#7c3aed",
      },
      {
        name: "Forecast Revenue",
        Amount: data.financial_performance.actual_vs_forecast.forecast_revenue,
        fill: "#a78bfa",
      },
    ];
  };

  return (
    <div className="space-y-6 text-left pb-12 print:p-0">
      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 print:hidden">
        <div>
          <p className="text-[10px] font-bold text-violet-600 dark:text-violet-400 uppercase tracking-widest block mb-1">
            Executive Control Tower
          </p>
          <h1 className="text-2xl font-black text-slate-800 dark:text-white leading-tight">
            Executive Business Intelligence Reports
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Executive-level view of revenue, profitability, pricing performance, market conditions, inventory health and business forecasts.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs px-3.5 py-2.5 rounded-xl transition duration-150 border border-slate-200 dark:border-slate-700 cursor-pointer disabled:opacity-50"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            <span>Refresh Report</span>
          </button>

          <button
            onClick={handleExportCSV}
            disabled={loading || !data}
            className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs px-3.5 py-2.5 rounded-xl transition duration-150 border border-slate-200 dark:border-slate-700 cursor-pointer disabled:opacity-50"
          >
            <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v16.5c0 .621.504 1.125 1.125 1.125h14.25c.621 0 1.125-.504 1.125-1.125V3M3.75 3h16.5M3.75 3v16.5M21 3v16.5M12 9h3.75m-3.75 3h3.75m-3.75 3h3.75M9 9h.008v.008H9V9zm0 3h.008v.008H9V12zm0 3h.008v.008H9V15z" />
            </svg>
            <span>Export CSV</span>
          </button>

          <button
            onClick={handleExportPDF}
            disabled={loading || !data}
            className="flex items-center gap-1.5 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-800 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition duration-150 shadow-sm cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 19.164l-.218.032c-1.35.2-2.568-.11-3.48-.755-.845-.6-1.28-1.537-1.28-2.61a3.053 3.053 0 011.02-2.22c.767-.689 1.86-1.077 3.07-1.107l.218-.005V19.16zM21.75 12c0 1.073-.435 2.01-1.28 2.61-.912.645-2.13.955-3.48.756l-.218-.032V8.922l.218.005c1.21.03 2.303.418 3.07 1.106.585.525 1.02 1.196 1.02 1.968v.004zM6.72 8.922v10.24M17.28 8.922v10.24M9.36 4.5h5.28m-5.28 0a2.25 2.25 0 00-2.25 2.25v2.172m7.53-4.422a2.25 2.25 0 012.25 2.25v2.172M9.36 4.5v4.422m5.28-4.422v4.422" />
            </svg>
            <span>Export PDF Report</span>
          </button>
        </div>
      </header>

      {/* Selectors Panel */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4 print:hidden">
        <div className="space-y-1 text-left">
          <label htmlFor="exec-prod-select" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Portfolio / Product Scope
          </label>
          <select
            id="exec-prod-select"
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          >
            <option value="all">Entire Catalog (All SKUs)</option>
            {products && products.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1 text-left">
          <label htmlFor="exec-start-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Start Date Filter
          </label>
          <input
            id="exec-start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>

        <div className="space-y-1 text-left">
          <label htmlFor="exec-end-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            End Date Filter
          </label>
          <input
            id="exec-end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>
      </section>

      {/* Loading state */}
      {loading && !data && (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500">
          <div className="w-10 h-10 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-4 font-semibold">Generating Executive Summary Report...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 rounded-2xl p-6 text-center max-w-xl mx-auto space-y-4">
          <h3 className="text-base font-bold text-red-800 dark:text-red-400">Report Loading Error</h3>
          <p className="text-xs text-red-600 dark:text-red-300">{error}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl cursor-pointer"
          >
            Retry Report
          </button>
        </div>
      )}

      {/* Main Report Body */}
      {data && !loading && (
        <div className="space-y-6">
          
          {/* 1. EXECUTIVE KPI SUMMARY */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4" aria-label="Executive Key Indicators">
            
            {/* Total Revenue */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Total Revenue</span>
                <strong className="text-lg font-black text-slate-800 dark:text-white leading-tight">
                  {formatCurrency(data.kpis.total_revenue)}
                </strong>
              </div>
              <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className="text-[10px] font-bold text-slate-500">Active portfolio earnings</span>
              </div>
            </article>

            {/* Gross Profit */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Gross Profit</span>
                <strong className="text-lg font-black text-slate-800 dark:text-white leading-tight">
                  {data.kpis.cost_data_available ? formatCurrency(data.kpis.gross_profit) : "₹ —"}
                </strong>
              </div>
              <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className="text-[10px] font-bold text-slate-500">Margin after unit cost</span>
              </div>
            </article>

            {/* Gross Margin */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Gross Margin</span>
                <strong className="text-lg font-black text-slate-800 dark:text-white leading-tight">
                  {data.kpis.cost_data_available && data.kpis.gross_margin !== null ? `${data.kpis.gross_margin.toFixed(1)}%` : "— %"}
                </strong>
              </div>
              <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className="text-[10px] font-bold text-slate-500">Profit contribution ratio</span>
              </div>
            </article>

            {/* Units Sold */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Units Sold</span>
                <strong className="text-lg font-black text-slate-800 dark:text-white leading-tight">
                  {data.kpis.units_sold.toLocaleString()}
                </strong>
              </div>
              <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className="text-[10px] font-bold text-slate-500">Cumulative sales volume</span>
              </div>
            </article>

            {/* Average Selling Price */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Avg Selling Price</span>
                <strong className="text-lg font-black text-slate-800 dark:text-white leading-tight">
                  {formatCurrency(data.kpis.average_selling_price)}
                </strong>
              </div>
              <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className="text-[10px] font-bold text-slate-500">Mean unit checkout value</span>
              </div>
            </article>

            {/* Revenue Growth */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <span className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Revenue Growth</span>
                <strong className="text-lg font-black text-emerald-600 dark:text-emerald-400 leading-tight">
                  +{data.kpis.revenue_growth.toFixed(1)}%
                </strong>
              </div>
              <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                <span className="text-[10px] font-bold text-slate-500">Growth relative to baseline</span>
              </div>
            </article>

          </section>

          {/* 2. BUSINESS PERFORMANCE CHARTS */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            
            {/* Historical Revenue & Profit Trend */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col">
              <div className="mb-4 text-left">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">Historical Revenue & Profit Trend</h3>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Month-by-month aggregated sales vs profit margins</p>
              </div>
              
              {(!data.financial_performance.trends || data.financial_performance.trends.length === 0) ? (
                <div className="bg-slate-50/50 dark:bg-slate-950/20 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Historical trend metrics are currently unavailable for this product scope.</p>
                </div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.financial_performance.trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#059669" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#059669" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                      <YAxis tickFormatter={formatChartCurrency} tick={{ fontSize: 10 }} />
                      <ChartTooltip formatter={(val) => formatCurrency(val)} />
                      <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                      <Area name="Monthly Revenue" type="monotone" dataKey="revenue" stroke="#7c3aed" strokeWidth={2.5} fillOpacity={1} fill="url(#colorRevenue)" />
                      {data.kpis.cost_data_available && (
                        <Area name="Monthly Profit" type="monotone" dataKey="profit" stroke="#059669" strokeWidth={2.5} fillOpacity={1} fill="url(#colorProfit)" />
                      )}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </article>

            {/* Actual Revenue vs Forecast Revenue */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col">
              <div className="mb-4 text-left">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">Actual Revenue vs Forecast Revenue</h3>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Baseline catalog performance matched against AI ML prediction models</p>
              </div>

              {(!data.financial_performance.actual_vs_forecast.actual_revenue && !data.financial_performance.actual_vs_forecast.forecast_revenue) ? (
                <div className="bg-slate-50/50 dark:bg-slate-950/20 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-400 dark:text-slate-500">Forecast comparison metrics are currently unavailable.</p>
                </div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getActualVsForecastData()} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                      <YAxis tickFormatter={formatChartCurrency} tick={{ fontSize: 10 }} />
                      <ChartTooltip formatter={(val) => formatCurrency(val)} />
                      <Bar name="Revenue Projection" dataKey="Amount" radius={[10, 10, 0, 0]} barSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </article>

          </section>

          {/* 3. PRICING & MARKET INTELLIGENCE */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <div className="mb-4 text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">Pricing & Market Intelligence Overview</h3>
              <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Competitive price positioning, pressure indices and clearance opportunities</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="border border-slate-100 dark:border-slate-800 rounded-xl p-4 flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Avg Market Price</span>
                <strong className="text-xl font-bold text-slate-800 dark:text-white mt-1">
                  {formatCurrency(data.pricing_intelligence.average_market_price)}
                </strong>
                <p className="text-[10px] text-slate-400 mt-2">Competitors catalog average</p>
              </div>

              <div className="border border-slate-100 dark:border-slate-800 rounded-xl p-4 flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Competitive Pressure</span>
                <strong className="text-xl font-bold text-violet-600 dark:text-violet-400 mt-1">
                  {data.pricing_intelligence.competitive_pressure.toFixed(1)}%
                </strong>
                <p className="text-[10px] text-slate-400 mt-2">Average competitor exposure</p>
              </div>

              <div className="border border-slate-100 dark:border-slate-800 rounded-xl p-4 flex flex-col justify-between col-span-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Price Positioning vs Market Average</span>
                <div className="flex items-center gap-3 mt-2">
                  <div className="flex-1 text-center bg-slate-50 dark:bg-slate-950 p-2 rounded-lg">
                    <span className="block text-[10px] font-bold text-rose-500">Above</span>
                    <strong className="text-base font-bold text-slate-800 dark:text-white">{data.pricing_intelligence.above_market_count}</strong>
                  </div>
                  <div className="flex-1 text-center bg-slate-50 dark:bg-slate-950 p-2 rounded-lg">
                    <span className="block text-[10px] font-bold text-emerald-500">Below</span>
                    <strong className="text-base font-bold text-slate-800 dark:text-white">{data.pricing_intelligence.below_market_count}</strong>
                  </div>
                  <div className="flex-1 text-center bg-slate-50 dark:bg-slate-950 p-2 rounded-lg">
                    <span className="block text-[10px] font-bold text-amber-500">At Price</span>
                    <strong className="text-base font-bold text-slate-800 dark:text-white">{data.pricing_intelligence.at_market_count}</strong>
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 mt-2">Catalog SKUs pricing distribution</p>
              </div>

              <div className="border border-slate-100 dark:border-slate-800 rounded-xl p-4 flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Opportunities / Risks</span>
                <div className="flex items-center justify-between gap-2 mt-2">
                  <div className="text-center flex-1 bg-emerald-50 dark:bg-emerald-950/20 p-2 text-emerald-600 rounded-lg">
                    <span className="block text-[9px] font-semibold">Opps</span>
                    <strong className="text-sm font-black">{data.pricing_intelligence.opportunities_count}</strong>
                  </div>
                  <div className="text-center flex-1 bg-rose-50 dark:bg-rose-950/20 p-2 text-rose-600 rounded-lg">
                    <span className="block text-[9px] font-semibold">Risks</span>
                    <strong className="text-sm font-black">{data.pricing_intelligence.risks_count}</strong>
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 mt-2">Actionable pricing signals</p>
              </div>
            </div>
          </section>

          {/* 4. PRODUCT PERFORMANCE TABLES */}
          <section className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            
            {/* Top 5 profitable products */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
              <div className="mb-4">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">Top 5 Profitable SKUs</h3>
                <p className="text-[10px] text-slate-400 mt-0.5">Highest absolute gross profit generators</p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="text-[10px] font-bold text-slate-400 uppercase border-b border-slate-100 dark:border-slate-800">
                      <th className="pb-2">Name</th>
                      <th className="pb-2 text-right">Profit</th>
                      <th className="pb-2 text-right">Margin %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {padTableData(data.product_performance.top_profitable).map((p, idx) => {
                      if (p.isPlaceholder) {
                        return (
                          <tr key={`profitable-placeholder-${idx}`} className="border-b border-slate-50 dark:border-slate-950/40 opacity-0">
                            <td className="py-2">&nbsp;</td>
                            <td className="py-2 text-right">&nbsp;</td>
                            <td className="py-2 text-right">&nbsp;</td>
                          </tr>
                        );
                      }
                      return (
                        <tr key={idx} className="border-b border-slate-50 dark:border-slate-950/40 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                          <td className="py-2 font-medium text-slate-800 dark:text-slate-200 truncate max-w-[140px]" title={p.product_name}>{p.product_name}</td>
                          <td className="py-2 text-right font-semibold text-slate-800 dark:text-white">
                            {formatCurrency(p.gross_profit)}
                          </td>
                          <td className="py-2 text-right">
                            <span className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 font-bold rounded-lg text-[10px]">
                              {p.gross_margin_percent?.toFixed(1)}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>

            {/* Top 5 revenue products */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
              <div className="mb-4">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">Top 5 Revenue SKUs</h3>
                <p className="text-[10px] text-slate-400 mt-0.5">Highest sales revenue generators</p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="text-[10px] font-bold text-slate-400 uppercase border-b border-slate-100 dark:border-slate-800">
                      <th className="pb-2">Name</th>
                      <th className="pb-2 text-right">Revenue</th>
                      <th className="pb-2 text-right">Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {padTableData(data.product_performance.top_revenue).map((p, idx) => {
                      if (p.isPlaceholder) {
                        return (
                          <tr key={`revenue-placeholder-${idx}`} className="border-b border-slate-50 dark:border-slate-950/40 opacity-0">
                            <td className="py-2">&nbsp;</td>
                            <td className="py-2 text-right">&nbsp;</td>
                            <td className="py-2 text-right">&nbsp;</td>
                          </tr>
                        );
                      }
                      return (
                        <tr key={idx} className="border-b border-slate-50 dark:border-slate-950/40 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                          <td className="py-2 font-medium text-slate-800 dark:text-slate-200 truncate max-w-[140px]" title={p.product_name}>{p.product_name}</td>
                          <td className="py-2 text-right font-semibold text-slate-800 dark:text-white">
                            {formatCurrency(p.revenue)}
                          </td>
                          <td className="py-2 text-right font-medium text-slate-500">{p.units_sold} units</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>

            {/* Low-margin products */}
            <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
              <div className="mb-4">
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">Low Margin/Risk SKUs</h3>
                <p className="text-[10px] text-slate-400 mt-0.5">Items with tightest profit spreads</p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="text-[10px] font-bold text-slate-400 uppercase border-b border-slate-100 dark:border-slate-800">
                      <th className="pb-2">Name</th>
                      <th className="pb-2 text-right">Margin %</th>
                      <th className="pb-2 text-right">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {padTableData(data.product_performance.low_margin).map((p, idx) => {
                      if (p.isPlaceholder) {
                        return (
                          <tr key={`margin-placeholder-${idx}`} className="border-b border-slate-50 dark:border-slate-950/40 opacity-0">
                            <td className="py-2">&nbsp;</td>
                            <td className="py-2 text-right">&nbsp;</td>
                            <td className="py-2 text-right">&nbsp;</td>
                          </tr>
                        );
                      }
                      return (
                        <tr key={idx} className="border-b border-slate-50 dark:border-slate-950/40 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                          <td className="py-2 font-medium text-slate-800 dark:text-slate-200 truncate max-w-[140px]" title={p.product_name}>{p.product_name}</td>
                          <td className="py-2 text-right">
                            <span className="px-2 py-0.5 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 font-bold rounded-lg text-[10px]">
                              {p.gross_margin_percent?.toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-2 text-right font-medium text-slate-500">
                            {formatCurrency(p.revenue)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>

          </section>

          {/* 5. INVENTORY & DEMAND HEALTH */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <div className="mb-4 text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">Inventory Safety & Demand Projections</h3>
              <p className="text-[10px] text-slate-400 mt-0.5">Alerts for imminent stockouts and slow-moving excess stock</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
              
              {/* stockout list */}
              <div className="space-y-3">
                <div className="flex justify-between items-center bg-rose-50 dark:bg-rose-950/10 p-3 rounded-xl border border-rose-100 dark:border-rose-900/30">
                  <span className="text-[10px] font-bold text-rose-800 dark:text-rose-400 uppercase">Critical Stockout Risks</span>
                  <span className="bg-rose-600 text-white font-black text-xs px-2 py-0.5 rounded-lg">{data.inventory_health.stockout_risks_count}</span>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {data.inventory_health.critical_inventory_risk.length === 0 ? (
                    <div className="p-3 bg-slate-50/50 dark:bg-slate-950 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg text-slate-400 text-xs py-4 text-center">
                      No immediate stockout risks detected.
                    </div>
                  ) : (
                    data.inventory_health.critical_inventory_risk.map((p, idx) => (
                      <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-950 rounded-lg flex items-center justify-between text-xs border border-slate-100 dark:border-slate-800/60">
                        <div>
                          <strong className="block text-slate-800 dark:text-slate-200 truncate max-w-[130px]" title={p.product_name}>{p.product_name}</strong>
                          <span className="text-[10px] text-slate-400">{p.stock} units left</span>
                        </div>
                        <span className="bg-rose-100 text-rose-700 font-bold px-2 py-0.5 rounded-lg text-[9px]">
                          {p.days_of_supply?.toFixed(1)} Days supply
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* excess stock list */}
              <div className="space-y-3">
                <div className="flex justify-between items-center bg-amber-50 dark:bg-amber-950/10 p-3 rounded-xl border border-amber-100 dark:border-amber-900/30">
                  <span className="text-[10px] font-bold text-amber-800 dark:text-amber-400 uppercase">Excess Stock Items</span>
                  <span className="bg-amber-600 text-white font-black text-xs px-2 py-0.5 rounded-lg">{data.inventory_health.excess_inventory_count}</span>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {data.inventory_health.excess_inventory.length === 0 ? (
                    <div className="p-3 bg-slate-50/50 dark:bg-slate-950 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg text-slate-400 text-xs py-4 text-center">
                      No excess inventory risks detected.
                    </div>
                  ) : (
                    data.inventory_health.excess_inventory.map((p, idx) => (
                      <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-950 rounded-lg flex items-center justify-between text-xs border border-slate-100 dark:border-slate-800/60">
                        <div>
                          <strong className="block text-slate-800 dark:text-slate-200 truncate max-w-[130px]" title={p.product_name}>{p.product_name}</strong>
                          <span className="text-[10px] text-slate-400">{p.stock} units in warehouse</span>
                        </div>
                        <span className="bg-amber-100 text-amber-700 font-bold px-2 py-0.5 rounded-lg text-[9px]">
                          {p.days_of_supply?.toFixed(1)} Days supply
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* demand forecast overview */}
              <div className="space-y-3">
                <div className="bg-slate-50 dark:bg-slate-950 p-4 rounded-xl flex flex-col justify-between border border-slate-100 dark:border-slate-800">
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase">Mean Days of Supply</span>
                    <strong className="text-2xl font-black text-slate-800 dark:text-white mt-1 block">
                      {data.inventory_health.average_days_of_supply.toFixed(1)} Days
                    </strong>
                    <p className="text-[10px] text-slate-400 mt-2">Overall portfolio coverage depth</p>
                  </div>

                  <div className="pt-4 border-t border-slate-200/60 dark:border-slate-800 mt-4">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase mb-2">Demand Forecast Signals</span>
                    <div className="flex gap-2 text-[10px] font-semibold">
                      <span className="flex-1 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 p-1.5 rounded text-center">
                        {data.demand_forecast.total_increasing} Increasing
                      </span>
                      <span className="flex-1 bg-rose-50 dark:bg-rose-950/20 text-rose-600 p-1.5 rounded text-center">
                        {data.demand_forecast.total_decreasing} Decreasing
                      </span>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </section>

          {/* 6. EXECUTIVE INSIGHTS */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <div className="mb-4 text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">Executive Insights</h3>
              <p className="text-[10px] text-slate-400 mt-0.5">AI-synthesized operational patterns and growth signals</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
              {data.insights.map((insight, idx) => (
                <div key={idx} className="p-3 bg-violet-50/40 dark:bg-violet-950/10 border border-violet-100/50 dark:border-violet-900/20 rounded-xl flex items-start gap-2.5">
                  <div className="p-1 bg-violet-500 text-white rounded-lg mt-0.5">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18h.01M12 6h.01M12 12h.01M12 18h.01" />
                      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2"/>
                    </svg>
                  </div>
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-medium">{insight}</p>
                </div>
              ))}
              {data.insights.length === 0 && (
                <div className="col-span-2 bg-slate-50/50 dark:bg-slate-950/20 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-400 dark:text-slate-500">No significant anomalies or operational insights generated.</p>
                </div>
              )}
            </div>
          </section>

          {/* 7. RECOMMENDED ACTIONS */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <div className="mb-4 text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">Recommended Management Actions</h3>
              <p className="text-[10px] text-slate-400 mt-0.5">Prioritized interventions to capture margins and mitigate inventory shortages</p>
            </div>

            <div className="space-y-3">
              {data.recommendations.map((action, idx) => (
                <article key={idx} className="border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 rounded-2xl p-4 hover:bg-slate-50/30 dark:hover:bg-slate-800/20 transition-all text-left">
                  <div className="flex flex-wrap items-center justify-between gap-2.5 mb-2.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        action.priority === "HIGH" 
                          ? "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400" 
                          : action.priority === "MEDIUM"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400"
                          : "bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-400"
                      }`}>
                        {action.priority} Priority
                      </span>
                      <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">{action.business_area}</span>
                    </div>
                  </div>

                  <h4 className="text-xs font-bold text-slate-900 dark:text-white mb-1">{action.recommendation}</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mb-2.5">{action.reason}</p>

                  <div className="p-2 bg-slate-50 dark:bg-slate-950 rounded-xl flex items-center gap-2 border border-slate-100 dark:border-slate-800/80">
                    <svg className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="text-[10px] flex flex-wrap items-center gap-1.5">
                      <span className="text-slate-400 uppercase font-semibold text-[8px] whitespace-nowrap">Expected Impact:</span>
                      <strong className="text-slate-700 dark:text-slate-200 font-bold">{action.expected_impact}</strong>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          {/* Report Footer */}
          <footer className="text-center text-[10px] text-slate-400 dark:text-slate-500 pt-6 border-t border-slate-100 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span>Report Scope: </span>
              <strong className="font-semibold text-slate-500 dark:text-slate-400">{data.scope.product_name}</strong>
            </div>
            <div>
              <span>Report generated at: </span>
              <strong className="font-semibold text-slate-500 dark:text-slate-400">{new Date().toLocaleString()}</strong>
            </div>
            <div className="flex items-center gap-1.5 justify-center">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping"></span>
              <span>Data Synced: Postgres & SQLite connected</span>
            </div>
          </footer>

        </div>
      )}
    </div>
  );
}
