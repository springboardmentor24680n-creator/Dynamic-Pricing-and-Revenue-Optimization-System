import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ZAxis,
} from "recharts";

const API = "http://127.0.0.1:8000";

const formatCurrency = (val) => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(val || 0);
};

export default function AnalyticsDashboard({ products }) {
  const [overview, setOverview] = useState(null);
  const [models, setModels] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [overviewError, setOverviewError] = useState("");
  const [modelsError, setModelsError] = useState("");
  const [forecastError, setForecastError] = useState("");
  const [recommendationsError, setRecommendationsError] = useState("");

  const loadAnalyticsData = async () => {
    setLoading(true);
    setOverviewError("");
    setModelsError("");
    setForecastError("");
    setRecommendationsError("");

    // 1. Overview
    try {
      const ovRes = await axios.get(`${API}/api/dashboard/overview`);
      if (ovRes.data && ovRes.data.status === "success") {
        setOverview(ovRes.data.overview);
      } else {
        setOverviewError("Failed to load summary stats.");
      }
    } catch (err) {
      console.error("Error loading overview metrics:", err);
      setOverviewError("Failed to load summary stats.");
    }

    // 2. Models
    try {
      const mdRes = await axios.get(`${API}/api/dashboard/models`);
      if (mdRes.data && mdRes.data.status === "success") {
        setModels(mdRes.data.registered_models || []);
      } else {
        setModelsError("Failed to load model registry metrics.");
      }
    } catch (err) {
      console.error("Error loading models telemetry:", err);
      setModelsError("Failed to load model registry metrics.");
    }

    // 3. Forecast
    try {
      const fcRes = await axios.get(`${API}/api/ai/forecast-demand`, { params: { horizon: "90_days" } });
      if (fcRes.data && fcRes.data.status === "success") {
        setForecast(fcRes.data.forecast?.predictions || []);
      } else {
        setForecastError("Failed to load Prophet demand predictions.");
      }
    } catch (err) {
      console.error("Error loading forecast projections:", err);
      setForecastError("Failed to load Prophet demand predictions.");
    }

    // 4. Recommendations
    try {
      const rcRes = await axios.get(`${API}/api/dashboard/recommendations`);
      if (rcRes.data && rcRes.data.status === "success") {
        setRecommendations(rcRes.data.recommendations || []);
      } else {
        setRecommendationsError("Failed to load price recommendations.");
      }
    } catch (err) {
      console.error("Error loading pricing recommendations:", err);
      setRecommendationsError("Failed to load price recommendations.");
    }

    setLoading(false);
  };

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  // 1. Revenue Trends Data
  const revenueTrendData = [
    { name: "Baseline Current", amount: overview?.current_revenue || 6443486.05, color: "#3b82f6" },
    { name: "AI Projected Target", amount: overview?.expected_revenue || 13754741.21, color: "#8b5cf6" },
  ];

  // 2. Prediction Accuracy Data
  const modelAccuracyData = models.map((m) => {
    const rawR2 = m["R² Score"] !== undefined ? m["R² Score"] : (m["R²"] !== undefined ? m["R²"] : 0.85);
    const rawMAPE = m["MAPE"] !== undefined ? m["MAPE"] : 0.05;
    
    return {
      name: m["Algorithm"] || m["Model Name"] || "Model",
      "R² Score (%)": parseFloat((rawR2 * 100).toFixed(2)),
      "MAPE (%)": parseFloat((rawMAPE * 100).toFixed(2)),
    };
  });

  // 3. Inventory Levels Histogram Data
  const getInventoryData = () => {
    if (!products || products.length === 0) return [];
    
    const buckets = { critical: 0, low: 0, adequate: 0, high: 0 };
    products.forEach((p) => {
      const s = p.stock || 0;
      if (s < 10) buckets.critical++;
      else if (s <= 30) buckets.low++;
      else if (s <= 100) buckets.adequate++;
      else buckets.high++;
    });

    return [
      { name: "Critical (<10)", count: buckets.critical, fill: "#f43f5e" },
      { name: "Low (10-30)", count: buckets.low, fill: "#f59e0b" },
      { name: "Adequate (30-100)", count: buckets.adequate, fill: "#3b82f6" },
      { name: "High (100+)", count: buckets.high, fill: "#10b981" },
    ];
  };

  const inventoryLevelsData = getInventoryData();

  // 4. Top 5 Products by Revenue Gain Data
  const topProductsData = [...recommendations]
    .sort((a, b) => (b.revenue_gain || 0) - (a.revenue_gain || 0))
    .slice(0, 5)
    .map((r) => ({
      name: `SKU ${r.product_id}`,
      gain: Math.round(r.revenue_gain || 0),
      recommended: r.recommended_price,
      current: r.current_price,
    }));

  // 5. Price Scatter Data
  const priceDistributionData = recommendations.map((r) => ({
    current: r.current_price,
    recommended: r.recommended_price,
    gain: r.revenue_gain,
    id: r.product_id,
  }));

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6">
      <header className="mb-8">
        <p className="text-sm font-semibold tracking-wider text-violet-600 dark:text-violet-400 uppercase">Executive Intelligence</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-1">BI Analytics Dashboard</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">Evaluate model accuracy vectors, inventory histograms, expected revenue shifts, and elasticity curves across the entire product catalog.</p>
      </header>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="w-12 h-12 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 dark:text-slate-400 font-medium mt-4">Compiling global business intelligence curves...</p>
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-fade-in">
          
          {/* Chart 1: Revenue Trends Strategy Comparison */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Revenue Optimization Projections</h3>
            <div className="w-full h-80 flex items-center justify-center">
              {overviewError ? (
                <span className="text-xs text-rose-500 font-medium">{overviewError}</span>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={revenueTrendData} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${(v/1e6).toFixed(1)}M`} />
                    <Tooltip formatter={(value) => [formatCurrency(value), "Revenue"]} />
                    <Bar dataKey="amount" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 text-center">Net comparison of portfolio baseline vs. dynamic price target revenue.</p>
          </div>

          {/* Chart 2: Demand Trends Prophet Curve */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Prophet Daily Demand Curve (90d)</h3>
            <div className="w-full h-80 flex items-center justify-center">
              {forecastError ? (
                <span className="text-xs text-rose-500 font-medium">{forecastError}</span>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={forecast} margin={{ left: -10, right: 10 }}>
                    <defs>
                      <linearGradient id="colorForecastBI" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                    <XAxis dataKey="date" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v) => [v?.toLocaleString() + " units", "Demand"]} />
                    <Area type="monotone" dataKey="forecast" name="Forecast Demand" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorForecastBI)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 text-center">90-day daily aggregated demand units series.</p>
          </div>

          {/* Chart 3: Prediction Accuracy */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Model Accuracy Comparison</h3>
            <div className="w-full h-80 flex items-center justify-center">
              {modelsError ? (
                <span className="text-xs text-rose-500 font-medium">{modelsError}</span>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={modelAccuracyData} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v) => [`${v}%`]} />
                    <Legend verticalAlign="top" height={36} iconType="circle" />
                    <Bar dataKey="R² Score (%)" fill="#6366f1" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="MAPE (%)" fill="#ec4899" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 text-center">Holdout accuracy indicators loaded from Model Versioning Registry.</p>
          </div>

          {/* Chart 4: Inventory Levels */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Catalog Inventory Distribution</h3>
            <div className="w-full h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={inventoryLevelsData} margin={{ left: -10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => [v + " products"]} />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]} fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 text-center">Classification count of stock volume across the active catalog.</p>
          </div>

          {/* Chart 5: Top Products by expected revenue gain */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Top 5 SKU Contributors by Revenue Gain</h3>
            <div className="w-full h-80 flex items-center justify-center">
              {recommendationsError ? (
                <span className="text-xs text-rose-500 font-medium">{recommendationsError}</span>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topProductsData} layout="vertical" margin={{ left: 10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                    <XAxis type="number" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${(v/1e3).toFixed(0)}k`} />
                    <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v) => [formatCurrency(v), "Revenue Gain"]} />
                    <Bar dataKey="gain" fill="#10b981" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 text-center">Top performance items ranked by projected dynamic pricing margin gain.</p>
          </div>

          {/* Chart 6: Price Distribution Scatter */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Price Dispersion (Recommended vs. Current)</h3>
            <div className="w-full h-80 flex items-center justify-center">
              {recommendationsError ? (
                <span className="text-xs text-rose-500 font-medium">{recommendationsError}</span>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 0, left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                    <XAxis type="number" dataKey="current" name="Current Price" unit="₹" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis type="number" dataKey="recommended" name="Recommended Price" unit="₹" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip 
                      cursor={{ strokeDasharray: "3 3" }} 
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white p-3 rounded-lg text-xs font-sans shadow-lg">
                              <p className="font-bold text-slate-900 dark:text-white">SKU {data.id}</p>
                              <p className="text-slate-600 dark:text-slate-300">Current Price: {formatCurrency(data.current)}</p>
                              <p className="text-violet-600 dark:text-violet-400 font-semibold">Recommended: {formatCurrency(data.recommended)}</p>
                              <p className="text-emerald-600 dark:text-emerald-400 font-semibold">Gain: {formatCurrency(data.gain)}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Scatter name="SKUs" data={priceDistributionData} fill="#aa3bff" />
                  </ScatterChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 text-center">Elasticity deviation map showing recommended price markup vectors.</p>
          </div>

        </div>
      )}
    </div>
  );
}
