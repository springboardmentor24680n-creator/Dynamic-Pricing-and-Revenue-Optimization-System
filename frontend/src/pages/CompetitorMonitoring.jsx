import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
} from "recharts";

export default function CompetitorMonitoring({
  products,
  token,
  API,
  setActiveView,
  showToast,
  formatCurrency,
}) {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [status, setStatus] = useState(null);
  const [latestPrices, setLatestPrices] = useState([]);
  const [historyData, setHistoryData] = useState([]);
  const [alertsList, setAlertsList] = useState([]);
  const [isTriggering, setIsTriggering] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [loadingPrices, setLoadingPrices] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingAlerts, setLoadingAlerts] = useState(false);

  // States and effects for toggling historical competitors on the chart
  const [selectedChartCompetitors, setSelectedChartCompetitors] = useState([]);

  useEffect(() => {
    if (historyData && historyData.length > 0) {
      const uniqueComps = Array.from(new Set(historyData.map((item) => item.competitor_name)));
      // Sort competitors by count of historical records (most relevant first)
      const counts = {};
      historyData.forEach((item) => {
        counts[item.competitor_name] = (counts[item.competitor_name] || 0) + 1;
      });
      const sorted = uniqueComps.sort((a, b) => (counts[b] || 0) - (counts[a] || 0));
      setSelectedChartCompetitors(sorted.slice(0, 5));
    } else {
      setSelectedChartCompetitors([]);
    }
  }, [historyData]);

  const toggleCompetitorLine = (compName) => {
    setSelectedChartCompetitors((prev) => {
      if (prev.includes(compName)) {
        return prev.filter((c) => c !== compName);
      } else {
        return [...prev, compName];
      }
    });
  };

  // Scheduler & API usage budget states
  const [schedulerStats, setSchedulerStats] = useState(null);
  const [apiUsage, setApiUsage] = useState(null);
  const [monitoringRuns, setMonitoringRuns] = useState([]);
  const [loadingScheduler, setLoadingScheduler] = useState(false);

  // Filter States
  const [selectedProductFilter, setSelectedProductFilter] = useState("all");
  const [selectedCompetitorFilter, setSelectedCompetitorFilter] = useState("all");
  const [selectedTrendFilter, setSelectedTrendFilter] = useState("all");
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState("all");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState("all"); // 'all', 'acknowledged', 'active'

  const headers = {
    Authorization: `Bearer ${token}`,
  };

  // 1. Load telemetry status
  const fetchStatus = async () => {
    setLoadingStatus(true);
    try {
      const res = await axios.get(`${API}/api/competitor-monitoring/status`, { headers });
      setStatus(res.data);
    } catch (err) {
      console.error("Error loading status:", err);
    } finally {
      setLoadingStatus(false);
    }
  };

  // Load scheduler telemetry and API budget detail
  const fetchSchedulerDetails = async () => {
    setLoadingScheduler(true);
    try {
      const [schedRes, usageRes, runsRes] = await Promise.all([
        axios.get(`${API}/api/competitor-monitoring/scheduler`, { headers }),
        axios.get(`${API}/api/competitor-monitoring/api-usage`, { headers }),
        axios.get(`${API}/api/competitor-monitoring/runs`, { headers })
      ]);
      setSchedulerStats(schedRes.data);
      setApiUsage(usageRes.data);
      setMonitoringRuns(runsRes.data);
    } catch (err) {
      console.error("Error loading scheduler details:", err);
    } finally {
      setLoadingScheduler(false);
    }
  };

  // 2. Load latest competitor prices
  const fetchLatestPrices = async () => {
    setLoadingPrices(true);
    try {
      const res = await axios.get(`${API}/api/competitor-monitoring/latest`, { headers });
      setLatestPrices(res.data);
    } catch (err) {
      console.error("Error loading latest prices:", err);
    } finally {
      setLoadingPrices(false);
    }
  };

  // 3. Load alerts list
  const fetchAlerts = async () => {
    setLoadingAlerts(true);
    try {
      const res = await axios.get(`${API}/api/competitor-monitoring/alerts`, { headers });
      setAlertsList(res.data);
    } catch (err) {
      console.error("Error loading alerts:", err);
    } finally {
      setLoadingAlerts(false);
    }
  };

  // 4. Load history for selected product
  const fetchHistory = async (prodId) => {
    if (!prodId) return;
    setLoadingHistory(true);
    try {
      const res = await axios.get(`${API}/api/competitor-monitoring/history/${prodId}`, { headers });
      setHistoryData(res.data);
    } catch (err) {
      console.error(`Error loading history for product ${prodId}:`, err);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Load initial data
  useEffect(() => {
    fetchStatus();
    fetchLatestPrices();
    fetchAlerts();
    fetchSchedulerDetails();
  }, []);

  // Update default selected product and load its history
  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      const firstId = String(products[0].id);
      setSelectedProductId(firstId);
      fetchHistory(firstId);
    }
  }, [products]);

  // Handle manual product selection change
  const handleProductChange = (e) => {
    const id = e.target.value;
    setSelectedProductId(id);
    fetchHistory(id);
  };

  // Trigger manual monitoring cycle
  const handleTriggerUpdate = async () => {
    setIsTriggering(true);
    try {
      const res = await axios.post(
        `${API}/api/competitor-monitoring/trigger-update`,
        {},
        { headers, timeout: 30000 }
      );
      if (res.data && res.data.status === "success") {
        showToast(
          `Scrape completed. Checked: ${res.data.competitors_checked}, Changes: ${res.data.price_changes_detected}, Alerts: ${res.data.alerts_generated}`,
          "success"
        );
        // Refresh all dashboards
        fetchStatus();
        fetchLatestPrices();
        fetchAlerts();
        fetchSchedulerDetails();
        if (selectedProductId) {
          fetchHistory(selectedProductId);
        }
      }
    } catch (err) {
      console.error("Error triggering update:", err);
      if (err.response && err.response.status === 409) {
        showToast("A competitor monitoring scan is already in progress. Please wait.", "warning");
      } else if (err.code === "ECONNABORTED") {
        showToast("Competitor monitoring scan request timed out. Retrying in background...", "warning");
      } else {
        showToast("Failed to run competitor monitoring update cycle.", "error");
      }
    } finally {
      setIsTriggering(false);
    }
  };

  // Acknowledge a specific alert
  const handleAcknowledge = async (alertId) => {
    try {
      const res = await axios.post(
        `${API}/api/competitor-monitoring/alerts/${alertId}/acknowledge`,
        {},
        { headers }
      );
      if (res.data && res.data.status === "success") {
        showToast(`Alert #${alertId} acknowledged.`, "success");
        // Update local alerts list state immediately
        setAlertsList((prev) =>
          prev.map((a) => (a.id === alertId ? { ...a, is_acknowledged: true } : a))
        );
        fetchStatus(); // Refresh active count
      }
    } catch (err) {
      console.error(`Error acknowledging alert ${alertId}:`, err);
      showToast("Failed to acknowledge alert.", "error");
    }
  };

  // Clear filters helper
  const handleClearFilters = () => {
    setSelectedProductFilter("all");
    setSelectedCompetitorFilter("all");
    setSelectedTrendFilter("all");
    setSelectedSeverityFilter("all");
    setSelectedStatusFilter("all");
  };

  // Get distinct competitors for filters dropdown
  const getUniqueCompetitors = () => {
    const set = new Set(latestPrices.map((p) => p.competitor_name));
    return Array.from(set);
  };

  // Process history records list to fit Recharts line requirements
  const getChartData = () => {
    if (!historyData || historyData.length === 0) return [];
    
    // Group price entries by date-time
    const dateMap = {};
    historyData.forEach((item) => {
      // Format to short date time
      const dateLabel = new Date(item.last_checked).toLocaleDateString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
      if (!dateMap[dateLabel]) {
        dateMap[dateLabel] = { name: dateLabel };
      }
      dateMap[dateLabel][item.competitor_name] = item.competitor_price;
    });

    // Sort by timestamp
    return Object.values(dateMap);
  };

  const getChartLines = () => {
    const competitors = new Set(historyData.map((item) => item.competitor_name));
    return Array.from(competitors);
  };

  // Filters application for Competitors Overview Table
  const getFilteredPrices = () => {
    return latestPrices.filter((item) => {
      if (selectedProductFilter !== "all" && String(item.product_id) !== String(selectedProductFilter)) {
        return false;
      }
      if (selectedCompetitorFilter !== "all" && item.competitor_name !== selectedCompetitorFilter) {
        return false;
      }
      if (selectedTrendFilter !== "all" && item.trend !== selectedTrendFilter) {
        return false;
      }
      return true;
    });
  };

  // Filters application for Alerts list
  const getFilteredAlerts = () => {
    return alertsList.filter((item) => {
      if (selectedProductFilter !== "all" && String(item.product_id) !== String(selectedProductFilter)) {
        return false;
      }
      if (selectedCompetitorFilter !== "all" && item.competitor_name !== selectedCompetitorFilter) {
        return false;
      }
      if (selectedSeverityFilter !== "all" && item.severity !== selectedSeverityFilter) {
        return false;
      }
      if (selectedStatusFilter !== "all") {
        if (selectedStatusFilter === "acknowledged" && !item.is_acknowledged) return false;
        if (selectedStatusFilter === "active" && item.is_acknowledged) return false;
      }
      return true;
    });
  };

  // Generate dynamic market insights from latest prices list
  const calculateInsights = () => {
    const selectedProd = products.find((p) => String(p.id) === String(selectedProductId));
    if (!selectedProd) return [];

    const activeProdPrices = latestPrices.filter(
      (p) => String(p.product_id) === String(selectedProductId)
    );
    if (activeProdPrices.length === 0) return ["No competitor pricing registered for this product."];

    const insights = [];
    let cheaperCount = 0;
    let expensiveCount = 0;
    let maxDiscountPercent = 0;
    let maxDiscountComp = "";
    
    activeProdPrices.forEach((c) => {
      const diff = selectedProd.current_price - c.competitor_price;
      const pct = (diff / c.competitor_price) * 100;
      
      if (diff > 0.01) {
        cheaperCount++;
        if (pct > maxDiscountPercent) {
          maxDiscountPercent = pct;
          maxDiscountComp = c.competitor_name;
        }
      } else if (diff < -0.01) {
        expensiveCount++;
      }
    });

    if (cheaperCount > 0) {
      insights.push(
        `${cheaperCount} competitor${cheaperCount > 1 ? "s are" : " is"} currently priced below us.`
      );
      if (maxDiscountComp) {
        insights.push(
          `${maxDiscountComp} offers the steepest discount, priced ${maxDiscountPercent.toFixed(1)}% below our current rate.`
        );
      }
      insights.push(
        "Competitor discount rates are putting downward margin pressure on our product."
      );
    } else {
      insights.push("We are currently matching or beating all local competitor pricing.");
    }

    if (expensiveCount > 0) {
      insights.push(
        `${expensiveCount} competitor${expensiveCount > 1 ? "s are" : " is"} priced above our SKU, signaling potential room for premium price optimization.`
      );
    }

    // General trend comments
    const standardChanges = activeProdPrices.filter((p) => p.trend !== "stable");
    if (standardChanges.length > 0) {
      insights.push(
        `Dynamic tracking registered ${standardChanges.length} recent price movement shifts across competitor products.`
      );
    }

    return insights;
  };

  const selectedProd = products.find((p) => String(p.id) === String(selectedProductId));
  const selectedPrices = latestPrices.filter((p) => String(p.product_id) === String(selectedProductId));
  const selectedAlerts = alertsList.filter((a) => String(a.product_id) === String(selectedProductId));

  // Determine the lowest competitor price for the selected product
  const getCheapestCompetitorPrice = () => {
    if (selectedPrices.length === 0) return null;
    const sorted = [...selectedPrices].sort((a, b) => a.competitor_price - b.competitor_price);
    return sorted[0];
  };

  const cheapestCompetitor = getCheapestCompetitorPrice();

  // Helper colors
  const getBadgeColor = (type) => {
    switch (type?.toLowerCase()) {
      case "high":
      case "significant_price_change":
      case "decreased":
      case "price_decrease":
        return "bg-rose-100 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50";
      case "medium":
      case "competitor_out_of_stock":
        return "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50";
      case "increased":
      case "price_increase":
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50";
      default:
        return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700";
    }
  };

  const filteredPrices = getFilteredPrices();
  const filteredAlerts = getFilteredAlerts();

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* 1. Header Copy */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-wider text-violet-600 dark:text-violet-400 uppercase">
            Market Intelligence
          </p>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-1">
            Competitor Monitoring
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2 text-sm max-w-2xl">
            Track competitor pricing, detect market changes, and identify pricing opportunities.
          </p>
        </div>
        <button
          onClick={handleTriggerUpdate}
          disabled={isTriggering}
          className="w-full md:w-auto px-5 py-3 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-semibold text-xs flex items-center justify-center gap-2 shadow transition cursor-pointer disabled:opacity-75"
        >
          {isTriggering ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Checking...</span>
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              <span>Check Now</span>
            </>
          )}
        </button>
      </header>

      {/* 2. Selector section */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <label htmlFor="comp-prod-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Selected Analysis Product
          </label>
          <span className="text-[11px] text-slate-400 block">
            Updates comparison charts, price history timeline curves, and target product impact.
          </span>
        </div>
        <select
          id="comp-prod-select"
          value={selectedProductId}
          onChange={handleProductChange}
          className="w-full md:w-80 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-semibold text-sm cursor-pointer"
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
      </section>

      {/* 3. Monitoring Status Cards */}
      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left relative overflow-hidden group">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Status</span>
          {loadingStatus ? (
            <div className="h-10 w-24 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <div className="flex flex-col gap-1 mt-2">
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${
                  status?.current_data_source === "pricesapi" || status?.current_data_source === "openwebninja" ? "bg-emerald-500 animate-ping" :
                  status?.data_source === "budget_exhausted" ? "bg-amber-500 animate-pulse" :
                  status?.data_source === "api_error" || status?.data_source === "rate_limit" || status?.status === "failed" ? "bg-rose-500" :
                  "bg-amber-500"
                }`}></span>
                <strong className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-tight">
                  {status?.current_data_source === "pricesapi" || status?.current_data_source === "openwebninja" ? "LIVE API" :
                   status?.data_source === "budget_exhausted" ? "BUDGET LIMIT" :
                   status?.data_source === "api_error" || status?.data_source === "rate_limit" || status?.status === "failed" ? "DATA SOURCE UNAVAILABLE" :
                   "SIMULATION / FALLBACK"}
                </strong>
              </div>
              <span className={`text-[9px] font-bold uppercase tracking-wide block ${
                status?.current_data_source === "pricesapi" || status?.current_data_source === "openwebninja" ? "text-emerald-600 dark:text-emerald-400" :
                status?.data_source === "budget_exhausted" ? "text-amber-600 dark:text-amber-400" :
                status?.data_source === "api_error" || status?.data_source === "rate_limit" || status?.status === "failed" ? "text-rose-600 dark:text-rose-400" :
                "text-amber-600 dark:text-amber-400"
              }`}>
                {status?.current_data_source === "pricesapi" ? "PricesAPI" :
                 status?.current_data_source === "openwebninja" ? "OpenWeb Ninja Backup" :
                 status?.data_source === "budget_exhausted" ? "● Budget Exhausted" :
                 status?.data_source === "api_error" || status?.data_source === "rate_limit" || status?.status === "failed" ? "● Providers Failed" :
                 "● Simulation / Fallback"}
              </span>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Last Scan</span>
          {loadingStatus ? (
            <div className="h-6 w-24 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-2 whitespace-nowrap overflow-hidden text-ellipsis">
              {status?.last_monitoring_run
                ? new Date(status.last_monitoring_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : "Never"}
            </span>
          )}
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Next Scan</span>
          {loadingStatus ? (
            <div className="h-6 w-24 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-2 whitespace-nowrap overflow-hidden text-ellipsis">
              {status?.next_scheduled_run
                ? new Date(status.next_scheduled_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : "N/A"}
            </span>
          )}
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Competitors</span>
          {loadingStatus ? (
            <div className="h-6 w-8 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
              {status?.competitors_found ?? status?.number_of_competitors_monitored ?? 0}
            </strong>
          )}
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Price Shifts</span>
          {loadingStatus ? (
            <div className="h-6 w-8 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong className="text-2xl font-black text-slate-800 dark:text-slate-100 block mt-1">
              {status?.number_of_price_changes_detected ?? 0}
            </strong>
          )}
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm text-left">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Active Alerts</span>
          {loadingStatus ? (
            <div className="h-6 w-8 bg-slate-200 dark:bg-slate-800 rounded animate-pulse mt-2"></div>
          ) : (
            <strong
              className={`text-2xl font-black block mt-1 ${
                (status?.number_of_active_alerts ?? 0) > 0 ? "text-rose-500" : "text-emerald-500"
              }`}
            >
              {status?.number_of_active_alerts ?? 0}
            </strong>
          )}
        </div>
      </section>

      {/* Scheduler & Request Budget Telemetry Section */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scheduler Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4 text-violet-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Monitoring Scheduler
              </h3>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                schedulerStats?.enabled
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
              }`}>
                {schedulerStats?.enabled ? "ACTIVE" : "DISABLED"}
              </span>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Monitoring:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {schedulerStats?.enabled ? "ACTIVE" : "INACTIVE"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Scan Interval:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  Every {schedulerStats?.interval_hours ?? 6} Hours
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Last Automated Scan:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {schedulerStats?.last_run?.started_at
                    ? new Date(schedulerStats.last_run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : "Never"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Next Scheduled Scan:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {schedulerStats?.next_run
                    ? new Date(schedulerStats.next_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : "N/A"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Products Due:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {schedulerStats?.products_due ?? 0}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Last Run Status:</span>
                <span className={`font-semibold uppercase ${
                  schedulerStats?.last_run?.status === "success" ? "text-emerald-500" :
                  schedulerStats?.last_run?.status === "budget_exhausted" ? "text-amber-500" :
                  schedulerStats?.last_run?.status === "failed" ? "text-rose-500" : "text-slate-500"
                }`}>
                  {schedulerStats?.last_run?.status ?? "NEVER RUN"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Data Source:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {status?.data_source === "openwebninja" ? "LIVE OPENWEB NINJA" :
                   status?.data_source === "budget_exhausted" ? "API BUDGET EXHAUSTED" :
                   status?.data_source === "api_error" || status?.data_source === "rate_limit" ? "API ERROR" :
                   "SIMULATION / FALLBACK"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* API Budget Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4 text-violet-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                API Request Budget
              </h3>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                apiUsage?.budget_status === "active"
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
                  : "bg-rose-100 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400"
              }`}>
                {apiUsage?.budget_status?.toUpperCase() ?? "ACTIVE"}
              </span>
            </div>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-500 dark:text-slate-400 font-medium">PricesAPI (Primary):</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {status?.prices_api_requests_used ?? 0} / {status?.monthly_limit ?? 1000}
                  </span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 mb-3">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${
                      status?.primary_status === "QUOTA EXCEEDED" ? "bg-rose-500" : "bg-violet-500"
                    }`}
                    style={{
                      width: `${Math.min(
                        100,
                        (((status?.prices_api_requests_used ?? 0) / (status?.monthly_limit ?? 1000)) * 100)
                      )}%`,
                    }}
                  ></div>
                </div>

                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-500 dark:text-slate-400 font-medium">OpenWeb Ninja (Backup):</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {status?.openweb_used_this_month ?? 0} / {status?.openweb_limit ?? 100}
                  </span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${
                      status?.backup_status === "QUOTA EXCEEDED" ? "bg-rose-500" : "bg-emerald-500"
                    }`}
                    style={{
                      width: `${Math.min(
                        100,
                        (((status?.openweb_used_this_month ?? 0) / (status?.openweb_limit ?? 100)) * 100)
                      )}%`,
                    }}
                  ></div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 border-t border-slate-100 dark:border-slate-800 pt-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">PricesAPI Remaining</span>
                  <span className="text-lg font-extrabold text-slate-800 dark:text-slate-200 block mt-0.5">
                    {status?.prices_api_requests_remaining ?? 1000}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Last Provider</span>
                  <span className="text-sm font-extrabold text-violet-600 dark:text-violet-400 block mt-1 uppercase">
                    {status?.last_successful_provider ?? "None"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Monitoring Runs History */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm text-left flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-3">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4 text-violet-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Execution Runs Log
              </h3>
            </div>
            
            <div className="space-y-2 overflow-y-auto max-h-[175px] pr-1">
              {monitoringRuns && monitoringRuns.length > 0 ? (
                monitoringRuns.slice(0, 5).map((run) => (
                  <div key={run.id} className="flex items-center justify-between p-2 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-xs border border-slate-100 dark:border-slate-800/50">
                    <div className="space-y-0.5 text-left">
                      <span className="font-bold text-slate-700 dark:text-slate-300 block">
                        {run.started_at
                          ? new Date(run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : "Unknown"}
                      </span>
                      <span className="text-[10px] text-slate-400 block uppercase">
                        {run.source} • {run.products_checked} SKU checked
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {run.api_requests > 0 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-violet-100 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 font-bold">
                          {run.api_requests} reqs
                        </span>
                      )}
                      <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                        run.status === "success"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
                          : run.status === "budget_exhausted"
                          ? "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400"
                          : "bg-rose-100 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400"
                      }`}>
                        {run.status?.toUpperCase() ?? "SUCCESS"}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-slate-400 text-xs">
                  No execution runs recorded yet.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 4. Filters Section */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left space-y-4">
        <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <svg className="w-4 h-4 text-violet-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
            </svg>
            Console Filter Engine
          </h3>
          <button
            onClick={handleClearFilters}
            className="text-xs text-violet-600 hover:text-violet-700 font-bold flex items-center gap-1 cursor-pointer"
          >
            Clear Filters
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Product</label>
            <select
              value={selectedProductFilter}
              onChange={(e) => setSelectedProductFilter(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer text-slate-800 dark:text-slate-200"
            >
              <option value="all">All Products</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Competitor</label>
            <select
              value={selectedCompetitorFilter}
              onChange={(e) => setSelectedCompetitorFilter(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer text-slate-800 dark:text-slate-200"
            >
              <option value="all">All Competitors</option>
              {getUniqueCompetitors().map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Trend</label>
            <select
              value={selectedTrendFilter}
              onChange={(e) => setSelectedTrendFilter(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer text-slate-800 dark:text-slate-200"
            >
              <option value="all">All Trends</option>
              <option value="increased">Price Increase</option>
              <option value="decreased">Price Decrease</option>
              <option value="stable">Stable</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Severity</label>
            <select
              value={selectedSeverityFilter}
              onChange={(e) => setSelectedSeverityFilter(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer text-slate-800 dark:text-slate-200"
            >
              <option value="all">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Alert Status</label>
            <select
              value={selectedStatusFilter}
              onChange={(e) => setSelectedStatusFilter(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer text-slate-800 dark:text-slate-200"
            >
              <option value="all">All Alerts</option>
              <option value="active">Active (Unack)</option>
              <option value="acknowledged">Acknowledged</option>
            </select>
          </div>
        </div>
      </section>

      {/* 5. Competitor Overview comparison table */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left space-y-4">
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Live Positions</span>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Competitor Price Catalog</h2>
        </div>
        <div className="table-wrap">
          {loadingPrices ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-500">
              <div className="w-8 h-8 border-3 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs text-slate-400 mt-2">Syncing competitor catalogs...</p>
            </div>
          ) : filteredPrices.length === 0 ? (
            <div className="p-10 text-center text-slate-500 dark:text-slate-400 font-medium text-xs">
              No competitor pricing records matches standard active filters.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Competitor</th>
                  <th>Product</th>
                  <th>Competitor Price</th>
                  <th>Our Price</th>
                  <th>Price Gap</th>
                  <th>% Gap</th>
                  <th>Availability</th>
                  <th>Last Sync</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {filteredPrices.map((item) => {
                  const matchingProduct = products.find((p) => String(p.id) === String(item.product_id));
                  const ourPrice = matchingProduct?.current_price ?? 0;
                  const priceDiff = ourPrice - item.competitor_price;
                  const percentDiff = item.competitor_price > 0 ? (priceDiff / item.competitor_price) * 100 : 0;

                  // Highlighting styles
                  let gapClass = "text-slate-500 dark:text-slate-400";
                  let bgHighlight = "";
                  if (priceDiff > 0.01) {
                    gapClass = "text-rose-500 font-bold"; // Competitor cheaper
                    bgHighlight = "bg-rose-50/20 dark:bg-rose-950/5";
                  } else if (priceDiff < -0.01) {
                    gapClass = "text-emerald-500 font-bold"; // Competitor more expensive
                    bgHighlight = "bg-emerald-50/20 dark:bg-emerald-950/5";
                  }

                  return (
                    <tr key={item.id} className={`${bgHighlight} hover:bg-slate-50/50 dark:hover:bg-slate-800/20`}>
                      <td className="font-semibold text-slate-800 dark:text-slate-200">{item.competitor_name}</td>
                      <td>
                        <div className="max-w-[160px] truncate text-slate-600 dark:text-slate-400" title={item.competitor_product_name}>
                          {matchingProduct ? matchingProduct.name : item.competitor_product_name}
                        </div>
                      </td>
                      <td className="font-mono text-slate-800 dark:text-slate-200">
                        {formatCurrency(item.competitor_price)}
                      </td>
                      <td className="font-mono text-slate-500 dark:text-slate-400">
                        {matchingProduct ? formatCurrency(ourPrice) : "N/A"}
                      </td>
                      <td className={`font-mono ${gapClass}`}>
                        {priceDiff > 0 ? "+" : ""}
                        {formatCurrency(priceDiff)}
                      </td>
                      <td className={`font-mono ${gapClass}`}>
                        {percentDiff > 0 ? "+" : ""}
                        {percentDiff.toFixed(1)}%
                      </td>
                      <td>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            item.availability === "In Stock"
                              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400"
                              : "bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-400"
                          }`}
                        >
                          {item.availability}
                        </span>
                      </td>
                      <td className="text-slate-400 dark:text-slate-500">
                        {item.last_checked
                          ? new Date(item.last_checked).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </td>
                      <td>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${getBadgeColor(item.trend)}`}>
                          {item.trend === "increased" && "↑ Increase"}
                          {item.trend === "decreased" && "↓ Decrease"}
                          {item.trend === "stable" && "→ Stable"}
                          {(!item.trend || item.trend === "stable") && "→ Stable"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* 6. Comparison Section & Price history */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Product Price Comparison Bars */}
        <div className="lg:col-span-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left">
          <div className="space-y-4">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SKU Comparison</span>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Our Price vs Competitors</h3>
            </div>
            
            <div className="space-y-4">
              {/* Our Price Card */}
              <div className="p-4 bg-violet-50/50 dark:bg-violet-950/10 border border-violet-100 dark:border-violet-900/30 rounded-xl relative">
                <span className="text-[9px] font-bold uppercase tracking-wider text-violet-500">Our Current Pricing</span>
                <div className="text-2xl font-black text-slate-800 dark:text-slate-100 mt-1">
                  {selectedProd ? formatCurrency(selectedProd.current_price) : "—"}
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Enterprise catalog baseline pricing</p>
              </div>

              {/* Competitors loop list */}
              {selectedPrices.length === 0 ? (
                <div className="text-xs text-slate-400 text-center py-6">
                  No competitors loaded for this product.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1.5">
                  {selectedPrices.map((c) => {
                    const priceDiff = (selectedProd?.current_price ?? 0) - c.competitor_price;
                    
                    return (
                      <div key={c.id} className="flex justify-between items-center p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200/50 dark:border-slate-800">
                        <div className="text-xs max-w-[65%]">
                          <strong className="font-bold text-slate-800 dark:text-slate-200 block truncate">{c.competitor_name}</strong>
                          <span className="text-[9px] text-slate-400 block truncate" title={c.competitor_product_name}>{c.competitor_product_name}</span>
                        </div>
                        <div className="text-right">
                          <strong className="text-xs font-mono text-slate-800 dark:text-slate-100 block">
                            {formatCurrency(c.competitor_price)}
                          </strong>
                          <span className={`text-[10px] font-mono ${priceDiff > 0 ? "text-rose-500 font-bold" : "text-emerald-500 font-bold"}`}>
                            {priceDiff > 0 ? "+" : ""}
                            {((priceDiff / c.competitor_price) * 100).toFixed(1)}% gap
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Recharts Line Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Historical Trend</span>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Competitor Price History</h3>
              </div>
              <span className="text-[10px] text-slate-400 font-semibold bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-lg">
                Showing {selectedChartCompetitors.length} lines
              </span>
            </div>

            {/* Custom interactive legend selector pills */}
            {historyData && historyData.length > 0 && (
              <div className="flex flex-wrap gap-1.5 max-h-[88px] overflow-y-auto pb-3 border-b border-slate-100 dark:border-slate-800 pr-1">
                {Array.from(new Set(historyData.map((item) => item.competitor_name))).map((compName, idx) => {
                  const isSelected = selectedChartCompetitors.includes(compName);
                  const colors = ["#8b5cf6", "#10b981", "#f59e0b", "#3b82f6", "#ec4899", "#06b6d4"];
                  const color = colors[idx % colors.length];
                  return (
                    <button
                      key={compName}
                      onClick={() => toggleCompetitorLine(compName)}
                      className={`px-2.5 py-1 rounded-full text-[10px] font-bold transition flex items-center gap-1.5 cursor-pointer ${
                        isSelected 
                          ? "text-white" 
                          : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                      }`}
                      style={isSelected ? { backgroundColor: color } : {}}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? "bg-white" : ""}`} style={!isSelected ? { backgroundColor: color } : {}}></span>
                      {compName}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="h-[320px] w-full mt-2">
            {loadingHistory ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <div className="w-8 h-8 border-3 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-xs text-slate-400 mt-2">Mapping historical index...</p>
              </div>
            ) : historyData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-xs text-slate-500 dark:text-slate-400 font-medium">
                No competitor price history entries found. Run scans to generate price timeline.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={getChartData()} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} dy={8} />
                  <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(val) => `₹${val}`} />
                  <ChartTooltip
                    contentStyle={{
                      backgroundColor: "rgba(30, 41, 59, 0.95)",
                      border: "none",
                      borderRadius: "12px",
                      color: "#fff",
                      fontSize: "11px",
                    }}
                    formatter={(val, name) => [formatCurrency(val), name]}
                    labelFormatter={(label) => `Time: ${label}`}
                  />
                  {getChartLines()
                    .filter((compName) => selectedChartCompetitors.includes(compName))
                    .map((compName) => {
                      const allComps = Array.from(new Set(historyData.map((item) => item.competitor_name)));
                      const idx = allComps.indexOf(compName);
                      const colors = ["#8b5cf6", "#10b981", "#f59e0b", "#3b82f6", "#ec4899", "#06b6d4"];
                      const color = colors[idx % colors.length];
                      return (
                        <Line
                          key={compName}
                          type="monotone"
                          dataKey={compName}
                          stroke={color}
                          strokeWidth={2}
                          dot={{ r: 2.5 }}
                          activeDot={{ r: 4.5 }}
                        />
                      );
                    })}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      {/* 7. Market Insights & Pricing Impact */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Dynamic Insights Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left space-y-4">
          <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Dynamic Signals</span>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Market Insights</h3>
          </div>
          <ul className="space-y-3 text-xs text-slate-600 dark:text-slate-400 font-medium">
            {calculateInsights().map((insight, idx) => (
              <li key={idx} className="flex gap-2">
                <span className="text-violet-500 font-bold">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Right: Pricing Impact & AI Recommendation shortcuts */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left flex flex-col justify-between">
          <div className="space-y-4">
            <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Revenue Impact</span>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Pricing Impact Summary</h3>
            </div>
            
            <div className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
              <div className="flex justify-between py-1 border-b border-slate-100/50 dark:border-slate-850">
                <span>Our Pricing Rate:</span>
                <strong className="text-slate-800 dark:text-slate-200">
                  {selectedProd ? formatCurrency(selectedProd.current_price) : "N/A"}
                </strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100/50 dark:border-slate-850">
                <span>Cheapest Competitor Rate:</span>
                <strong className="text-slate-800 dark:text-slate-200">
                  {cheapestCompetitor ? formatCurrency(cheapestCompetitor.competitor_price) : "N/A"}
                </strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100/50 dark:border-slate-850">
                <span>Direct Market Gap:</span>
                {cheapestCompetitor && selectedProd ? (
                  <strong
                    className={
                      selectedProd.current_price > cheapestCompetitor.competitor_price
                        ? "text-rose-500 font-bold"
                        : "text-emerald-500 font-bold"
                    }
                  >
                    {formatCurrency(selectedProd.current_price - cheapestCompetitor.competitor_price)} (
                    {(
                      ((selectedProd.current_price - cheapestCompetitor.competitor_price) /
                        cheapestCompetitor.competitor_price) *
                      100
                    ).toFixed(1)}
                    %)
                  </strong>
                ) : (
                  <strong>N/A</strong>
                )}
              </div>
              <div className="flex justify-between py-1">
                <span>Market Pricing Pressure:</span>
                {cheapestCompetitor && selectedProd ? (
                  <span
                    className={`font-semibold ${
                      selectedProd.current_price > cheapestCompetitor.competitor_price
                        ? "text-rose-500"
                        : "text-emerald-500"
                    }`}
                  >
                    {selectedProd.current_price > cheapestCompetitor.competitor_price
                      ? "▼ High Downward Pressure"
                      : "▲ Stable / Upward Capacity"}
                  </span>
                ) : (
                  <span>None</span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => setActiveView("ai_recommendation")}
            className="w-full mt-4 px-4 py-3 bg-violet-50 hover:bg-violet-100 text-violet-600 dark:bg-violet-950/20 dark:hover:bg-violet-950/30 dark:text-violet-400 rounded-xl text-xs font-semibold cursor-pointer border border-violet-200/50 dark:border-violet-900/30 text-center transition"
          >
            View AI Recommendation
          </button>
        </div>
      </section>

      {/* 8. Alert Center */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left space-y-4">
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Action Center</span>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Active Pricing Alerts</h2>
        </div>

        <div className="table-wrap">
          {loadingAlerts ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-500">
              <div className="w-8 h-8 border-3 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs text-slate-400 mt-2">Loading action center logs...</p>
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="p-10 text-center text-slate-500 dark:text-slate-400 font-medium text-xs">
              No active competitor alerts logs matching current filters.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Competitor</th>
                  <th>Product</th>
                  <th>Event Type</th>
                  <th>Prev Price</th>
                  <th>Current Price</th>
                  <th>Change %</th>
                  <th>Severity</th>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredAlerts.map((a) => {
                  const product = products.find((p) => String(p.id) === String(a.product_id));
                  return (
                    <tr key={a.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20">
                      <td className="font-semibold text-slate-800 dark:text-slate-200">{a.competitor_name}</td>
                      <td>
                        <div className="max-w-[140px] truncate" title={product?.name ?? a.product_id}>
                          {product ? product.name : a.product_id}
                        </div>
                      </td>
                      <td>
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${getBadgeColor(a.event_type)}`}>
                          {a.event_type?.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td>{a.previous_price ? formatCurrency(a.previous_price) : "—"}</td>
                      <td>{formatCurrency(a.current_price)}</td>
                      <td className={`font-mono font-bold ${a.change_percent >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                        {a.change_percent ? `${a.change_percent >= 0 ? "+" : ""}${a.change_percent.toFixed(1)}%` : "0%"}
                      </td>
                      <td>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                            a.severity === "high"
                              ? "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"
                              : a.severity === "medium"
                              ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                              : "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400"
                          }`}
                        >
                          {a.severity?.toUpperCase()}
                        </span>
                      </td>
                      <td className="text-slate-400 dark:text-slate-500 text-xs">
                        {new Date(a.created_at).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            a.is_acknowledged
                              ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                              : "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50"
                          }`}
                        >
                          {a.is_acknowledged ? "Acknowledged" : "Active"}
                        </span>
                      </td>
                      <td>
                        {!a.is_acknowledged ? (
                          <button
                            onClick={() => handleAcknowledge(a.id)}
                            className="px-3 py-1 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-[10px] font-bold transition shadow-sm cursor-pointer"
                          >
                            Acknowledge
                          </button>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
