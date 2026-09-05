import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const API = "http://127.0.0.1:8000";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const forecastVal = payload.find((p) => p.dataKey === "forecast")?.value;
    const lowerVal = payload.find((p) => p.dataKey === "lower_bound")?.value;
    const upperVal = payload.find((p) => p.dataKey === "upper_bound")?.value;
    
    return (
      <div className="bg-white dark:bg-slate-950/95 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white p-4 rounded-xl shadow-xl text-left font-sans backdrop-blur">
        <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mb-2">{label}</p>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-500"></span>
            <span className="text-sm font-bold">
              Predicted: {forecastVal?.toLocaleString()} units
            </span>
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-300 pl-4">
            Lower Bound: {lowerVal?.toLocaleString()} units
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-300 pl-4">
            Upper Bound: {upperVal?.toLocaleString()} units
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function ForecastVisualization() {
  const [forecasts, setForecasts] = useState(null);
  const [activeHorizon, setActiveHorizon] = useState("90_days");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchForecasts = async () => {
    setLoading(true);
    setError("");
    try {
      // Fetch Prophet predictions for all horizons (7, 30, 90 days)
      const response = await axios.get(`${API}/api/ai/forecast-demand`, {
        params: { horizon: "all" },
      });
      if (response.data && response.data.status === "success") {
        setForecasts(response.data.forecasts);
      } else {
        setError("Invalid response format received from forecasting service.");
      }
    } catch (err) {
      console.error("Error loading forecast data:", err);
      setError(
        err.response?.data?.detail || "Failed to load Prophet demand projections from backend."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecasts();
  }, []);

  const getHorizonLabel = (key) => {
    switch (key) {
      case "7_days":
        return "7-Day Short-Term";
      case "30_days":
        return "30-Day Medium-Term";
      case "90_days":
        return "90-Day Long-Term";
      default:
        return key;
    }
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

  const activeForecast = forecasts ? forecasts[activeHorizon] : null;
  const chartData = activeForecast ? activeForecast.predictions : [];

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6">
      <header className="mb-8">
        <p className="text-sm font-semibold tracking-wider text-violet-600 dark:text-violet-400 uppercase">Demand Forecasting</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-1">Prophet Demand Projections</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">Evaluate seasonal sales fluctuations, future demand velocity metrics, and confidence bands across multiple time horizons.</p>
      </header>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="w-12 h-12 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 dark:text-slate-400 font-medium mt-4">Running Prophet time-series calculations...</p>
        </div>
      )}

      {error && (
        <div className="p-6 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400 mb-8">
          <h4 className="font-bold">Error Querying Forecasting Service</h4>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchForecasts}
            className="mt-3 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-semibold text-xs transition"
          >
            Retry Fetch
          </button>
        </div>
      )}

      {forecasts && activeForecast && (
        <div className="animate-fade-in">
          {/* Horizon Selection Tabs */}
          <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4 mb-8">
            {Object.keys(forecasts).map((horizonKey) => (
              <button
                key={horizonKey}
                onClick={() => setActiveHorizon(horizonKey)}
                className={`py-3 px-4 text-sm font-semibold border-b-2 transition duration-200 -mb-px ${
                  activeHorizon === horizonKey
                    ? "border-violet-600 text-violet-600 dark:text-violet-400"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 dark:text-slate-400 dark:hover:text-slate-200"
                }`}
              >
                {getHorizonLabel(horizonKey)}
              </button>
            ))}
          </div>

          {/* Telemetry Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total Projected Demand</span>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                {activeForecast.total_predicted_demand?.toLocaleString()} units
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Cumulative volume forecast for {activeForecast.horizon_days} days</p>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Average Daily Demand</span>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                {activeForecast.average_daily_demand?.toLocaleString()} units/day
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Mean daily velocity over horizon period</p>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Forecast Confidence</span>
                <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${getConfidenceBadgeColor(activeForecast.confidence_score_percent)}`}>
                  {activeForecast.confidence_score_percent >= 85 ? "High" : activeForecast.confidence_score_percent >= 70 ? "Medium" : "Low"}
                </span>
              </div>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                {activeForecast.confidence_score_percent}%
              </div>
              <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full mt-3 overflow-hidden">
                <div 
                  className="h-full bg-violet-600 dark:bg-violet-400 rounded-full" 
                  style={{ width: `${activeForecast.confidence_score_percent}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Time Series Chart */}
          <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm mb-8">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-6">Predicted Demand Curve</h3>
            <div className="w-full h-96">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#94a3b8" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={false} 
                    dy={10}
                  />
                  <YAxis 
                    stroke="#94a3b8" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={false} 
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    verticalAlign="top" 
                    height={36} 
                    iconType="circle"
                    formatter={(value) => <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">{value}</span>}
                  />
                  
                  {/* Shaded Area for expected forecast values */}
                  <Area 
                    type="monotone" 
                    dataKey="forecast" 
                    name="Predicted Demand" 
                    stroke="#8b5cf6" 
                    strokeWidth={2.5} 
                    fillOpacity={1} 
                    fill="url(#colorForecast)" 
                  />
                  
                  {/* Lower Uncertainty Bound */}
                  <Line 
                    type="monotone" 
                    dataKey="lower_bound" 
                    name="Lower Bound" 
                    stroke="#c084fc" 
                    strokeWidth={1} 
                    strokeDasharray="4 4" 
                    dot={false} 
                  />
                  
                  {/* Upper Uncertainty Bound */}
                  <Line 
                    type="monotone" 
                    dataKey="upper_bound" 
                    name="Upper Bound" 
                    stroke="#c084fc" 
                    strokeWidth={1} 
                    strokeDasharray="4 4" 
                    dot={false} 
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* General Model Meta */}
          <section className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800/60 rounded-2xl p-6 text-left">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">Forecasting Engine Specification</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Projections are computed using the Facebook Prophet additive time-series regression model. Seasonal parameters integrate weekly and yearly cyclic demand frequencies. Uncertainty bounds correspond to a 80% model confidence interval (derived from trend error variance simulated via Monte Carlo iterations).
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
