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
} from "recharts";

export default function PricingComparisonReports({
  products,
  token,
  API,
  showToast,
  formatCurrency,
}) {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedCompetitor, setSelectedCompetitor] = useState("all");
  const [uniqueCompetitors, setUniqueCompetitors] = useState([]);
  
  const [stats, setStats] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);

  // Set default product on load
  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      setSelectedProductId(products[0].id);
    }
  }, [products, selectedProductId]);

  // Load comparison statistics and history data
  useEffect(() => {
    if (!selectedProductId) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const params = {
          start_date: startDate || undefined,
          end_date: endDate || undefined,
          competitor: selectedCompetitor !== "all" ? selectedCompetitor : undefined,
        };

        // 1. Fetch Comparison Stats
        const statsRes = await axios.get(`${API}/api/pricing-comparison/${selectedProductId}`, {
          headers,
          params,
        });
        setStats(statsRes.data);

        // Extract unique competitors list for this product to update filters dropdown
        if (statsRes.data?.listings) {
          const comps = Array.from(new Set(statsRes.data.listings.map((l) => l.competitor_name)));
          setUniqueCompetitors(comps);
        }

        // 2. Fetch History Points
        const historyRes = await axios.get(`${API}/api/pricing-comparison/${selectedProductId}/history`, {
          headers,
          params,
        });
        setHistoryData(historyRes.data);
      } catch (err) {
        console.error("Error loading pricing reports data:", err);
        showToast("Failed to load pricing comparison metrics.", "error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedProductId, startDate, endDate, selectedCompetitor, token, API, showToast]);

  const handleExportPDF = async () => {
    if (!selectedProductId) return;
    setExportingPdf(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API}/api/pricing-comparison/${selectedProductId}/export/pdf`, {
        headers,
        params: {
          start_date: startDate || undefined,
          end_date: endDate || undefined,
          competitor: selectedCompetitor !== "all" ? selectedCompetitor : undefined,
        },
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/pdf" });
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `pricing_comparison_report_${selectedProductId}.pdf`;
      link.click();
      showToast("PDF comparison report downloaded successfully.", "success");
    } catch (err) {
      console.error("PDF export failed:", err);
      showToast("Failed to export PDF pricing report.", "error");
    } finally {
      setExportingPdf(false);
    }
  };

  const handleExportCSV = async () => {
    if (!selectedProductId) return;
    setExportingCsv(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API}/api/pricing-comparison/${selectedProductId}/export/csv`, {
        headers,
        params: {
          start_date: startDate || undefined,
          end_date: endDate || undefined,
          competitor: selectedCompetitor !== "all" ? selectedCompetitor : undefined,
        },
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "text/csv" });
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `pricing_comparison_report_${selectedProductId}.csv`;
      link.click();
      showToast("CSV comparison spreadsheet downloaded successfully.", "success");
    } catch (err) {
      console.error("CSV export failed:", err);
      showToast("Failed to export CSV pricing spreadsheet.", "error");
    } finally {
      setExportingCsv(false);
    }
  };

  // Process data for Price Comparison Bar Chart
  const getBarChartData = () => {
    if (!stats || !stats.listings) return [];
    
    // Add our product price
    const data = [
      {
        name: "Our Price",
        price: stats.our_current_price,
        isOurs: true,
      },
    ];

    stats.listings.forEach((lst) => {
      data.push({
        name: lst.competitor_name,
        price: lst.competitor_price,
        isOurs: false,
      });
    });

    return data;
  };

  const barData = getBarChartData();

  return (
    <div className="space-y-6">
      {/* 1. Header Section */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold text-violet-600 dark:text-violet-400 uppercase tracking-widest block mb-1">
            Reports
          </p>
          <h1 className="text-2xl font-black text-slate-800 dark:text-white leading-tight">
            Pricing Comparison Reports
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Generate and export deep competitive pricing comparison metrics against active market competitors.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportPDF}
            disabled={exportingPdf || loading || !stats}
            className="flex items-center gap-2 bg-rose-600 hover:bg-rose-700 disabled:bg-rose-800 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition duration-150 shadow-sm"
          >
            {exportingPdf ? (
              <span>Exporting PDF...</span>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
                <span>Export PDF</span>
              </>
            )}
          </button>

          <button
            onClick={handleExportCSV}
            disabled={exportingCsv || loading || !stats}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-800 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition duration-150 shadow-sm"
          >
            {exportingCsv ? (
              <span>Exporting CSV...</span>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
                <span>Export CSV/Excel</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* 2. Selectors Panel */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Product selector */}
        <div className="space-y-1">
          <label htmlFor="report-prod-select" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Selected Product
          </label>
          <select
            id="report-prod-select"
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
        <div className="space-y-1">
          <label htmlFor="report-start-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Start Date
          </label>
          <input
            id="report-start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>

        {/* End Date */}
        <div className="space-y-1">
          <label htmlFor="report-end-date" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            End Date
          </label>
          <input
            id="report-end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          />
        </div>

        {/* Competitor Selector */}
        <div className="space-y-1">
          <label htmlFor="report-comp-select" className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Competitor Filter
          </label>
          <select
            id="report-comp-select"
            value={selectedCompetitor}
            onChange={(e) => setSelectedCompetitor(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-xs cursor-pointer"
          >
            <option value="all">All Competitors</option>
            {uniqueCompetitors.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Loading state indicator */}
      {loading && (
        <div className="flex items-center justify-center p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
          <span className="text-xs font-semibold text-slate-500 ml-3">Calculating metrics...</span>
        </div>
      )}

      {/* Main Report Dashboard */}
      {!loading && stats && (
        <div className="space-y-6">
          {/* 3. KPI Cards Grid */}
          <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Market Position / Rank */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left relative overflow-hidden group">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Market Position</span>
              <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                {stats.market_position_rank}
              </strong>
              <div className="flex items-center gap-1.5 mt-2">
                <span className={`w-2 h-2 rounded-full ${
                  stats.market_position === "lowest" ? "bg-emerald-500 animate-pulse" :
                  stats.market_position === "highest" ? "bg-rose-500" :
                  "bg-amber-500"
                }`}></span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  {stats.market_position.replace("_", " ")}
                </span>
              </div>
            </div>

            {/* 2. Price Gap Avg */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Price Gap (vs Avg)</span>
              <strong className={`text-2xl font-black block mt-1 ${
                stats.price_gap_absolute > 0 ? "text-rose-500" : stats.price_gap_absolute < 0 ? "text-emerald-500" : "text-slate-700 dark:text-slate-300"
              }`}>
                {stats.price_gap_absolute > 0 ? "+" : ""}{formatCurrency(stats.price_gap_absolute)}
              </strong>
              <span className={`text-[10px] font-bold uppercase tracking-wider block mt-2 ${
                stats.price_gap_absolute > 0 ? "text-rose-600 dark:text-rose-400" : stats.price_gap_absolute < 0 ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500"
              }`}>
                {stats.price_gap_percent > 0 ? "+" : ""}{stats.price_gap_percent.toFixed(1)}% Gap
              </span>
            </div>

            {/* 3. Competitive Pressure */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Competitive Pressure</span>
              <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
                {stats.competitive_pressure.toFixed(1)}%
              </strong>
              
              <div className="mt-3.5 h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full ${
                    stats.competitive_pressure > 50 ? "bg-rose-500" : stats.competitive_pressure > 20 ? "bg-amber-500" : "bg-emerald-500"
                  }`} 
                  style={{ width: `${stats.competitive_pressure}%` }}
                ></div>
              </div>
            </div>

            {/* 4. Price Range */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Market Pricing Range</span>
              <strong className="text-sm font-bold text-slate-700 dark:text-slate-300 block mt-2">
                Min: {formatCurrency(stats.lowest_competitor_price)}
              </strong>
              <strong className="text-sm font-bold text-slate-700 dark:text-slate-300 block mt-1">
                Max: {formatCurrency(stats.highest_competitor_price)}
              </strong>
            </div>
          </section>

          {/* 4. Key Insights Panel */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
              Key Business Insights
            </h2>
            <ul className="space-y-2">
              {stats.insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                  <span className="text-violet-500 mt-0.5">&bull;</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* 5. Visualizations Section */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Price Position Bar Chart */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Price Gap Analysis (Our Price vs Market)
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
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
                      {barData.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.isOurs ? "#8B5CF6" : "#94A3B8"} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Historical Trend Line Chart */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm text-left">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Historical Price Index Comparison
              </h3>
              <div className="h-64">
                {historyData && historyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={historyData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis 
                        dataKey="date" 
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
                        name="Our Price" 
                        type="monotone" 
                        dataKey="our_price" 
                        stroke="#8B5CF6" 
                        strokeWidth={2.5} 
                        dot={false}
                      />
                      <Line 
                        name="Lowest Competitor" 
                        type="monotone" 
                        dataKey="lowest" 
                        stroke="#10B981" 
                        strokeWidth={1.5}
                        dot={false}
                      />
                      <Line 
                        name="Market Average" 
                        type="monotone" 
                        dataKey="average" 
                        stroke="#64748B" 
                        strokeWidth={1.5}
                        strokeDasharray="4 4"
                        dot={false}
                      />
                      <Line 
                        name="Highest Competitor" 
                        type="monotone" 
                        dataKey="highest" 
                        stroke="#EF4444" 
                        strokeWidth={1.5}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-400">No historical comparison points recorded in this period.</span>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* 6. Competitor Pricing Matrix Table */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left">
            <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
              Competitor Ranking Matrix
            </h3>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="pb-3 pr-4">Competitor</th>
                    <th className="pb-3 pr-4">Competitor Product SKU</th>
                    <th className="pb-3 pr-4">Competitor Price</th>
                    <th className="pb-3 pr-4">Price Gap</th>
                    <th className="pb-3 pr-4">Percentage Gap</th>
                    <th className="pb-3 pr-4">Availability</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {stats.listings && stats.listings.map((lst, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition duration-150">
                      <td className="py-3 pr-4 font-bold text-slate-800 dark:text-slate-200">
                        {lst.competitor_name}
                      </td>
                      <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                        {lst.competitor_product_name}
                      </td>
                      <td className="py-3 pr-4 font-black">
                        {formatCurrency(lst.competitor_price)}
                      </td>
                      <td className={`py-3 pr-4 font-bold ${
                        lst.price_gap_absolute > 0 ? "text-rose-500" : lst.price_gap_absolute < 0 ? "text-emerald-500" : "text-slate-500"
                      }`}>
                        {lst.price_gap_absolute > 0 ? "+" : ""}{formatCurrency(lst.price_gap_absolute)}
                      </td>
                      <td className={`py-3 pr-4 font-bold ${
                        lst.price_gap_percent > 0 ? "text-rose-500" : lst.price_gap_percent < 0 ? "text-emerald-500" : "text-slate-500"
                      }`}>
                        {lst.price_gap_percent > 0 ? "+" : ""}{lst.price_gap_percent.toFixed(1)}%
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          lst.availability === "In Stock" ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400" : "bg-rose-50 text-rose-600 dark:bg-rose-950/30 dark:text-rose-400"
                        }`}>
                          {lst.availability}
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
