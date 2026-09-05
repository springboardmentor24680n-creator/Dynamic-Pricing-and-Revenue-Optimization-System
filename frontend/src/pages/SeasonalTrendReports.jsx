import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function SeasonalTrendReports({ products }) {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case "high demand":
      case "increasing":
      case "strong":
      case "healthy":
        return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/40";
      case "low demand":
      case "decreasing":
      case "risk of stockout":
        return "bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-400 border border-rose-200 dark:border-rose-900/40";
      case "monitor":
      case "moderate":
        return "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-400 border border-amber-200 dark:border-amber-900/40";
      case "excess inventory":
        return "bg-sky-50 text-sky-700 dark:bg-sky-950/20 dark:text-sky-400 border border-sky-200 dark:border-sky-900/40";
      default:
        return "bg-slate-50 text-slate-700 dark:bg-slate-800/40 dark:text-slate-400 border border-slate-200 dark:border-slate-800/50";
    }
  };

  const selectedProduct = products.find((p) => String(p.id) === String(selectedProductId));

  const fetchSeasonalTrends = async (id) => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      const response = await axios.get(`${API}/api/seasonal-trends/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setTrendData(response.data);
    } catch (err) {
      console.error("Error loading seasonal trends:", err);
      setError(
        err.response?.data?.detail || "Failed to load seasonal trend reports from AI module."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      const firstId = String(products[0].id);
      setSelectedProductId(firstId);
      fetchSeasonalTrends(firstId);
    }
  }, [products]);

  const handleProductChange = (e) => {
    const id = e.target.value;
    setSelectedProductId(id);
    fetchSeasonalTrends(id);
  };

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6 space-y-6">
      <header className="mb-6">
        <p className="text-sm font-semibold tracking-wider text-emerald-600 dark:text-emerald-400 uppercase">Revenue Intelligence</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">Seasonal Trend Reports</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">Analyze historical demand patterns, seasonality, pricing behavior and inventory trends.</p>
      </header>

      {/* Product Selector */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <label htmlFor="trend-prod-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Select Product to Analyze</label>
          <span className="text-[11px] text-slate-400 block">Calculates product-specific seasonal indices and demand trends from historical sales data.</span>
        </div>
        <select
          id="trend-prod-select"
          value={selectedProductId}
          onChange={handleProductChange}
          className="w-full md:w-80 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium text-sm cursor-pointer"
        >
          {products && products.length > 0 ? (
            products.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))
          ) : (
            <option value="">No products available</option>
          )}
        </select>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400 text-left">
          <h4 className="font-bold">Error</h4>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-3">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Analyzing seasonal data...</span>
        </div>
      ) : trendData && (
        <>
          {trendData.average_demand === null || trendData.average_demand <= 0 ? (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <span className="text-4xl block">📊</span>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">Insufficient Historical Data</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Product <strong>{trendData.product_name}</strong> currently has no sales history recorded. Establish transaction logs to enable seasonal trend calculations.
              </p>
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Demand Trend</span>
                  <span className={`inline-flex items-center px-2 py-0.5 mt-2 rounded-full text-xs font-bold ${getStatusColor(trendData.trend)}`}>
                    {trendData.trend}
                  </span>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Seasonality Strength</span>
                  <span className={`inline-flex items-center px-2 py-0.5 mt-2 rounded-full text-xs font-bold ${getStatusColor(trendData.seasonality)}`}>
                    {trendData.seasonality}
                  </span>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Peak Period</span>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-2 block">
                    {trendData.peak_period}
                  </span>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Low-Demand Period</span>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-2 block">
                    {trendData.low_period}
                  </span>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Average Demand</span>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-2 block">
                    {trendData.average_demand.toFixed(1)} units/mo
                  </span>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Revenue Trend</span>
                  <span className={`inline-flex items-center px-2 py-0.5 mt-2 rounded-full text-xs font-bold ${getStatusColor(trendData.revenue_trend)}`}>
                    {trendData.revenue_trend}
                  </span>
                </div>
              </div>

              {/* Chart & Deep Dives */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* SVG Chart Card */}
                <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                    📈 Monthly Seasonal Demand Pattern
                  </h3>
                  
                  <div className="bg-slate-50 dark:bg-slate-950/40 p-4 rounded-2xl border border-slate-150 dark:border-slate-800 flex items-center justify-center">
                    {(() => {
                      const points = trendData.seasonal_breakdown;
                      const maxVal = Math.max(0.1, ...points.map(p => p.average_demand)) * 1.25;

                      const width = 600;
                      const height = 200;
                      const paddingLeft = 40;
                      const paddingRight = 20;
                      const paddingTop = 20;
                      const paddingBottom = 30;

                      const chartWidth = width - paddingLeft - paddingRight;
                      const chartHeight = height - paddingTop - paddingBottom;

                      const getX = (idx) => paddingLeft + (idx / (points.length - 1)) * chartWidth;
                      const getY = (val) => height - paddingBottom - (val / maxVal) * chartHeight;

                      // Build path string
                      let pathD = "";
                      let areaD = `M ${getX(0)} ${getY(0)}`;
                      
                      points.forEach((p, idx) => {
                        const x = getX(idx);
                        const y = getY(p.average_demand);
                        if (idx === 0) {
                          pathD += `M ${x} ${y}`;
                        } else {
                          pathD += ` L ${x} ${y}`;
                        }
                        areaD += ` L ${x} ${y}`;
                      });
                      
                      areaD += ` L ${getX(points.length - 1)} ${getY(0)} Z`;

                      return (
                        <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-2xl h-auto text-slate-500 dark:text-slate-400 font-sans">
                          <defs>
                            <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                              <stop offset="100%" stopColor="#10b981" stopOpacity="0.00" />
                            </linearGradient>
                          </defs>

                          {/* Grid Lines */}
                          <line x1={paddingLeft} y1={getY(0)} x2={width - paddingRight} y2={getY(0)} stroke="currentColor" strokeWidth="1" strokeOpacity="0.15" />
                          <line x1={paddingLeft} y1={getY(maxVal / 2)} x2={width - paddingRight} y2={getY(maxVal / 2)} stroke="currentColor" strokeWidth="1" strokeOpacity="0.08" strokeDasharray="3 3" />
                          <line x1={paddingLeft} y1={getY(maxVal)} x2={width - paddingRight} y2={getY(maxVal)} stroke="currentColor" strokeWidth="1" strokeOpacity="0.08" strokeDasharray="3 3" />

                          {/* Y-axis Labels */}
                          <text x={paddingLeft - 8} y={getY(0) + 3} textAnchor="end" className="text-[9px] fill-current">0</text>
                          <text x={paddingLeft - 8} y={getY(maxVal / 2) + 3} textAnchor="end" className="text-[9px] fill-current">{(maxVal / 2).toFixed(1)}</text>
                          <text x={paddingLeft - 8} y={getY(maxVal) + 3} textAnchor="end" className="text-[9px] fill-current">{maxVal.toFixed(1)}</text>

                          {/* Shaded Area */}
                          <path d={areaD} fill="url(#area-grad)" />

                          {/* Trend Line */}
                          <path d={pathD} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />

                          {/* Data Nodes */}
                          {points.map((p, idx) => (
                            <circle key={idx} cx={getX(idx)} cy={getY(p.average_demand)} r="3.5" className="fill-emerald-500 stroke-white stroke-2 hover:r-5 transition cursor-pointer" />
                          ))}

                          {/* X-axis Month Labels */}
                          {points.map((p, idx) => {
                            if (idx % 2 !== 0) return null; // Show every alternate month to avoid crowd
                            return (
                              <text key={idx} x={getX(idx)} y={height - paddingBottom + 12} textAnchor="middle" className="text-[8px] fill-current font-semibold">
                                {p.period.substring(0, 3)}
                              </text>
                            );
                          })}
                        </svg>
                      );
                    })()}
                  </div>
                </div>

                {/* Analysis Deep Dives */}
                <div className="lg:col-span-1 space-y-6">
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                      Peak & Low Demand Analysis
                    </h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Peak Period:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">{trendData.peak_period}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Peak Demand:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">{trendData.peak_demand.toFixed(1)} units</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Low Period:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">{trendData.low_period}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Lowest Demand:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">{trendData.low_demand.toFixed(1)} units</span>
                      </div>
                      <div className="flex justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                        <span className="text-slate-500">Demand Difference:</span>
                        <span className="font-bold text-rose-500">{(trendData.peak_demand - trendData.low_demand).toFixed(1)} units</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                      Inventory & Seasonality
                    </h3>
                    <div className="space-y-3 text-sm text-left">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500">Inventory Status:</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${getStatusColor(trendData.inventory_status)}`}>
                          {trendData.inventory_status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                        {trendData.inventory_status === "Risk of Stockout" 
                          ? `Warning: Current stock level (${selectedProduct?.stock} units) is below the expected peak demand requirements of ${trendData.peak_demand.toFixed(1)} units. Stockouts may occur during the seasonal peak.` 
                          : `Current stock level is sufficient to sustain expected demand peaks.`}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Pricing & Demand Analysis */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4 text-left">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                  Pricing & Demand Correlation Analysis
                </h3>
                <p className="text-sm text-slate-700 dark:text-slate-350 leading-relaxed font-semibold">
                  {trendData.price_demand_relationship}
                </p>
              </div>

              {/* Seasonal Breakdown Table */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Seasonal Breakdown
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left text-slate-700 dark:text-slate-350">
                    <thead className="text-xs uppercase bg-slate-50 dark:bg-slate-950 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                      <tr>
                        <th className="px-6 py-3.5 font-semibold">Period</th>
                        <th className="px-6 py-3.5 font-semibold">Average Demand</th>
                        <th className="px-6 py-3.5 font-semibold">Revenue</th>
                        <th className="px-6 py-3.5 font-semibold">Average Price</th>
                        <th className="px-6 py-3.5 font-semibold">Inventory</th>
                        <th className="px-6 py-3.5 font-semibold">Demand Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 bg-white dark:bg-slate-900">
                      {trendData.seasonal_breakdown.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                          <td className="px-6 py-3.5 font-semibold text-slate-900 dark:text-white">
                            {row.period}
                          </td>
                          <td className="px-6 py-3.5">
                            {row.average_demand.toFixed(1)} units
                          </td>
                          <td className="px-6 py-3.5">
                            {formatCurrency(row.revenue)}
                          </td>
                          <td className="px-6 py-3.5">
                            {formatCurrency(row.average_price)}
                          </td>
                          <td className="px-6 py-3.5">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${getStatusColor(row.inventory_status)}`}>
                              {row.inventory} units ({row.inventory_status})
                            </span>
                          </td>
                          <td className="px-6 py-3.5">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${getStatusColor(row.demand_status)}`}>
                              {row.demand_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Insights and Recommendations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
                {/* Insights */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                    AI Seasonal Insights
                  </h3>
                  <ul className="space-y-3">
                    {trendData.insights.map((insight, idx) => (
                      <li key={idx} className="text-sm font-semibold text-slate-700 dark:text-slate-350 flex gap-2.5 items-start">
                        <span className="text-emerald-500 mt-0.5">✔</span>
                        <span>{insight}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Recommendations */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                    Recommended Actions
                  </h3>
                  <ul className="space-y-3">
                    {trendData.recommendations.map((recommendation, idx) => (
                      <li key={idx} className="text-sm font-semibold text-slate-700 dark:text-slate-350 flex gap-2.5 items-start">
                        <span className="text-violet-500 mt-0.5">⚡</span>
                        <span>{recommendation}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
