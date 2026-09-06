"use client";

import React from "react";
import { 
  TrendingUp, 
  DollarSign, 
  Target, 
  BarChart2, 
  BrainCircuit, 
  ArrowUpRight, 
  Sparkles, 
  Layers, 
  Users, 
  Zap,
  Activity
} from "lucide-react";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  BarChart, 
  Bar 
} from "recharts";

const OVERVIEW_METRICS_DATA = [
  { month: "Jan", baseline_revenue: 125000, optimized_revenue: 139000, demand_index: 85 },
  { month: "Feb", baseline_revenue: 132000, optimized_revenue: 148500, demand_index: 88 },
  { month: "Mar", baseline_revenue: 141000, optimized_revenue: 161000, demand_index: 94 },
  { month: "Apr", baseline_revenue: 138000, optimized_revenue: 156000, demand_index: 91 },
  { month: "May", baseline_revenue: 152000, optimized_revenue: 174000, demand_index: 98 },
  { month: "Jun", baseline_revenue: 168000, optimized_revenue: 195000, demand_index: 106 },
  { month: "Jul", baseline_revenue: 175000, optimized_revenue: 204000, demand_index: 112 },
  { month: "Aug", baseline_revenue: 182000, optimized_revenue: 216000, demand_index: 118 },
];

const MODEL_ACCURACY_DATA = [
  { model: "LightGBM", accuracy: 94.2, speed: "Fastest (4ms)", type: "Tabular Boosting" },
  { model: "XGBoost", accuracy: 93.6, speed: "Fast (12ms)", type: "Elasticity Regressor" },
  { model: "Prophet", accuracy: 91.8, speed: "Medium (28ms)", type: "Time-Series Seasonal" },
];

interface OverviewProps {
  onNavigateToCatalog: () => void;
}

export const OverviewDashboard: React.FC<OverviewProps> = ({
  onNavigateToCatalog
}) => {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Top Welcome Hero Banner */}
      <div className="bg-gradient-to-r from-brand-600 via-blue-600 to-indigo-700 text-white rounded-2xl p-8 shadow-card relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 text-white text-xs font-semibold backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-blue-200" />
            Autonomous Multi-Agent Dynamic Pricing Engine
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight">
            Revenue Intelligence & Price Optimization Platform
          </h2>
          <p className="text-blue-100 text-sm leading-relaxed">
            Maximize gross margins, forecast multi-horizon demand curves, and automate product pricing using integrated LightGBM, XGBoost, and Prophet models orchestrated by OpenRouter AI.
          </p>

          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={onNavigateToCatalog}
              className="bg-white text-brand-700 hover:bg-blue-50 font-bold px-5 py-2.5 rounded-xl text-sm transition-all shadow-md flex items-center gap-2"
            >
              <Layers className="w-4 h-4" />
              Explore Product Catalog & Run Predictions
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Projected Revenue Lift</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-3xl font-extrabold text-slate-900">+14.8%</p>
            <p className="text-xs text-emerald-600 font-semibold flex items-center gap-1 mt-1">
              <ArrowUpRight className="w-3.5 h-3.5" />
              +$34,200/mo estimated growth
            </p>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Prediction Accuracy</span>
            <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center border border-brand-100">
              <Target className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-3xl font-extrabold text-slate-900">93.2%</p>
            <p className="text-xs text-slate-500 font-medium mt-1">
              Ensemble (LightGBM + XGBoost + Prophet)
            </p>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Multi-AI Agents</span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center border border-purple-100">
              <BrainCircuit className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-3xl font-extrabold text-slate-900">3 Agents</p>
            <p className="text-xs text-purple-600 font-semibold mt-1">
              OpenRouter + Tavily + News API
            </p>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Catalog Optimization</span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-3xl font-extrabold text-slate-900">6 Products</p>
            <p className="text-xs text-slate-500 font-medium mt-1">
              Short, Medium & Long Term Horizons
            </p>
          </div>
        </div>
      </div>

      {/* Revenue Optimization Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div>
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-brand-600" />
                Baseline vs AI-Optimized Revenue Trajectory
              </h3>
              <p className="text-xs text-slate-500">
                Monthly revenue comparison showing dynamic pricing impact over baseline static pricing.
              </p>
            </div>

            <div className="flex items-center gap-4 text-xs font-semibold">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-slate-300" />
                <span className="text-slate-600">Static Pricing</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-brand-600" />
                <span className="text-brand-700">PricePilot AI</span>
              </div>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={OVERVIEW_METRICS_DATA} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorOptimized" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorBaseline" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false}
                  tickFormatter={(val) => `$${val / 1000}k`}
                />
                <Tooltip 
                  formatter={(val: any) => [`$${Number(val).toLocaleString()}`, "Revenue"]}
                  contentStyle={{ backgroundColor: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}
                />
                <Area type="monotone" dataKey="baseline_revenue" stroke="#94a3b8" strokeWidth={2} fillOpacity={1} fill="url(#colorBaseline)" name="Static Baseline" />
                <Area type="monotone" dataKey="optimized_revenue" stroke="#2563eb" strokeWidth={3} fillOpacity={1} fill="url(#colorOptimized)" name="PricePilot AI" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Model Accuracy Breakdown */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 mb-1">
              <Activity className="w-5 h-5 text-emerald-600" />
              ML Prediction Engine Performance
            </h3>
            <p className="text-xs text-slate-500 mb-6">
              Accuracy benchmarking across LightGBM, XGBoost, and Prophet models.
            </p>

            <div className="space-y-4">
              {MODEL_ACCURACY_DATA.map((item, i) => (
                <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-brand-600" />
                      {item.model}
                    </span>
                    <span className="text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-mono">
                      {item.accuracy}% Accuracy
                    </span>
                  </div>
                  
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-brand-600 h-2 rounded-full transition-all duration-500" 
                      style={{ width: `${item.accuracy}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-0.5">
                    <span>Type: {item.type}</span>
                    <span className="font-mono text-slate-700">{item.speed}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>Model Refresh Frequency</span>
            <span className="font-semibold text-slate-800">Real-time / Automated</span>
          </div>
        </div>
      </div>
    </div>
  );
};
