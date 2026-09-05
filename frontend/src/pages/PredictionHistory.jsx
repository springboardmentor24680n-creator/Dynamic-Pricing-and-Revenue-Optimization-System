import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function PredictionHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [modelFilter, setModelFilter] = useState("all");
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const fetchHistory = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await axios.get(`${API}/api/dashboard/history`);
      if (response.data && response.data.status === "success") {
        setHistory(response.data.prediction_history || []);
      } else {
        setError("Invalid response format received from logging service.");
      }
    } catch (err) {
      console.error("Error loading prediction history:", err);
      setError(
        err.response?.data?.detail || "Failed to retrieve prediction logs from MongoDB."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  // Filter logic
  const filteredLogs = history.filter((log) => {
    const matchesSearch = searchQuery === "" || 
      String(log.product_id || "").toLowerCase().includes(searchQuery.toLowerCase());
      
    const matchesModel = modelFilter === "all" || 
      String(log.model_used || "").toLowerCase().includes(modelFilter.toLowerCase());
      
    return matchesSearch && matchesModel;
  });

  // Unique model list for dropdown filter options
  const uniqueModels = Array.from(
    new Set(history.map((h) => h.model_used).filter(Boolean))
  );

  // Pagination logic
  const totalItems = filteredLogs.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedLogs = filteredLogs.slice(startIndex, startIndex + pageSize);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, modelFilter, pageSize]);

  // Delta percentage styling
  const renderPriceDelta = (current, recommended) => {
    if (!current || !recommended) return <span>-</span>;
    const diff = recommended - current;
    const pct = ((diff / current) * 100).toFixed(1);
    
    if (diff > 0.01) {
      return (
        <span className="inline-flex items-center text-xs font-bold text-emerald-600 dark:text-emerald-400">
          ▲ +{pct}%
        </span>
      );
    }
    if (diff < -0.01) {
      return (
        <span className="inline-flex items-center text-xs font-bold text-rose-600 dark:text-rose-400">
          ▼ {pct}%
        </span>
      );
    }
    return <span className="text-slate-500 dark:text-slate-400 font-bold text-xs">─ 0.0%</span>;
  };

  const getConfidenceBadgeColor = (score) => {
    if (score >= 85) {
      return "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900/50";
    }
    if (score >= 70) {
      return "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900/50";
    }
    return "bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-900/50";
  };

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6">
      <header className="mb-8">
        <p className="text-sm font-semibold tracking-wider text-violet-600 dark:text-violet-400 uppercase">Operational Audit</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-1">Prediction History Logs</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">Browse the searchable audit logs of prediction triggers served by the dynamic pricing models.</p>
      </header>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="w-12 h-12 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 dark:text-slate-400 font-medium mt-4">Retrieving database prediction history logs...</p>
        </div>
      )}

      {error && (
        <div className="p-6 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400 mb-8">
          <h4 className="font-bold">Error Querying History Logs</h4>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-6 animate-fade-in">
          
          {/* Search & Filter Header controls */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center gap-4 justify-between">
            <div className="flex-1 max-w-md">
              <label htmlFor="sku-search" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Search by Product ID</label>
              <input
                id="sku-search"
                type="text"
                placeholder="Type SKU or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-medium text-sm"
              />
            </div>

            <div className="w-full md:w-64">
              <label htmlFor="model-filter-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Filter by Model</label>
              <select
                id="model-filter-select"
                value={modelFilter}
                onChange={(e) => setModelFilter(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-medium text-sm"
              >
                <option value="all">All Models</option>
                {uniqueModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* Tabular Log Table */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-slate-600 dark:text-slate-300">
                <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                  <tr>
                    <th className="py-4 px-6">Product ID</th>
                    <th className="py-4 px-6">Current Price</th>
                    <th className="py-4 px-6">Recommended</th>
                    <th className="py-4 px-6">Delta</th>
                    <th className="py-4 px-6">Forecast Demand</th>
                    <th className="py-4 px-6">Model Used</th>
                    <th className="py-4 px-6">Confidence</th>
                    <th className="py-4 px-6">Timestamp</th>
                    <th className="py-4 px-6">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {paginatedLogs.length > 0 ? (
                    paginatedLogs.map((log, index) => (
                      <tr key={index} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                        <td className="py-4 px-6 font-semibold text-slate-900 dark:text-white">
                          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-xs">
                            {log.product_id || "N/A"}
                          </span>
                        </td>
                        <td className="py-4 px-6">{formatCurrency(log.current_price)}</td>
                        <td className="py-4 px-6 font-bold text-violet-600 dark:text-violet-400">
                          {formatCurrency(log.recommended_price)}
                        </td>
                        <td className="py-4 px-6">
                          {renderPriceDelta(log.current_price, log.recommended_price)}
                        </td>
                        <td className="py-4 px-6 font-medium">
                          {log.forecast_demand ? Math.round(log.forecast_demand).toLocaleString() : "0"} units
                        </td>
                        <td className="py-4 px-6 text-xs text-slate-500 dark:text-slate-400">
                          {log.model_used || "LightGBM"}
                        </td>
                        <td className="py-4 px-6">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-semibold border ${getConfidenceBadgeColor(log.confidence || 85)}`}>
                            {log.confidence ? log.confidence.toFixed(1) : "85.0"}%
                          </span>
                        </td>
                        <td className="py-4 px-6 text-xs text-slate-500 dark:text-slate-400">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : "N/A"}
                        </td>
                        <td className="py-4 px-6">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
                            Success
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="9" className="text-center py-10 text-slate-500 dark:text-slate-400">
                        No prediction history records match the filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 p-4 bg-slate-50/50 dark:bg-slate-800/20 text-xs">
                <div className="flex items-center gap-2 text-slate-500">
                  <span>Show</span>
                  <select
                    value={pageSize}
                    onChange={(e) => setPageSize(Number(e.target.value))}
                    className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-1 text-slate-800 dark:text-slate-300 focus:outline-none"
                  >
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                  </select>
                  <span>entries | Total: {totalItems} logs</span>
                </div>

                <div className="flex items-center gap-4">
                  <button
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                    className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 disabled:opacity-50 transition cursor-pointer"
                  >
                    Prev
                  </button>
                  <span className="font-semibold text-slate-600 dark:text-slate-400">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                    className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 disabled:opacity-50 transition cursor-pointer"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
