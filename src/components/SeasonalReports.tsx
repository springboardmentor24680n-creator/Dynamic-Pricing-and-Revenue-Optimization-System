"use client";

import React, { useState, useEffect } from "react";
import { Calendar, TrendingUp, AlertTriangle, CheckCircle2, Sparkles, Layers, ArrowUpRight } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export const SeasonalReports: React.FC = () => {
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/seasonal-reports")
      .then((res) => res.json())
      .then((data) => setReport(data))
      .catch(() => {
        setReport({
          title: "Q3-Q4 Executive Seasonal & Festival Demand Insights Report",
          summary: "High seasonal elasticity detected across Electronics, Gaming, and Home Appliances due to upcoming Q4 holiday shopping and festival demand.",
          weekly_patterns: [
            { day: "Monday", demand_index: 0.92, note: "Baseline inventory replenishment day" },
            { day: "Tuesday", demand_index: 0.95, note: "Steady B2B & corporate procurement" },
            { day: "Wednesday", demand_index: 1.02, note: "Mid-week discount campaign response" },
            { day: "Thursday", demand_index: 1.05, note: "Pre-weekend browsing spike" },
            { day: "Friday", demand_index: 1.28, note: "Peak conversion & weekend shopping trigger" },
            { day: "Saturday", demand_index: 1.35, note: "Highest consumer order volume" },
            { day: "Sunday", demand_index: 1.15, note: "Late evening mobile purchasing" }
          ],
          seasonal_factors: [
            { factor: "Back-To-School / Office Upgrade", impact: "+18.4% Demand Lift", affected_categories: ["Electronics", "Furniture"] },
            { factor: "Q4 Holiday & Festival Season", impact: "+34.2% Peak Surge", affected_categories: ["Gaming", "Home Appliances", "Electronics"] },
            { factor: "New Year Fitness Spike", impact: "+22.5% Demand Lift", affected_categories: ["Wearables"] }
          ],
          inventory_turnover_alerts: [
            { product: "Ergonomic Mesh Office Chair", stock: 75, days_remaining: 5.4, action: "Urgent Reorder Required" },
            { product: "Ultra-Wide 4K Monitor 34-inch", stock: 95, days_remaining: 9.2, action: "Optimal Stock Level" }
          ]
        });
      });
  }, []);

  if (!report) return null;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-bold mb-2">
          <Calendar className="w-3.5 h-3.5" />
          Seasonal Intelligence Module
        </div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">{report.title}</h2>
        <p className="text-slate-600 text-xs mt-1 max-w-3xl leading-relaxed">{report.summary}</p>
      </div>

      {/* Day of Week Pattern Chart */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card space-y-4">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-brand-600" />
          Day-of-Week Demand Index Distribution
        </h3>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={report.weekly_patterns} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 1.5]} />
              <Tooltip
                formatter={(val: any) => [`${val} Index`, "Demand Factor"]}
                contentStyle={{ backgroundColor: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0" }}
              />
              <Bar dataKey="demand_index" fill="#2563eb" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Seasonal Factors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {report.seasonal_factors.map((item: any, i: number) => (
          <div key={i} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-card space-y-3">
            <span className="text-xs font-bold text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-0.5 rounded-full">
              {item.impact}
            </span>
            <h4 className="text-base font-bold text-slate-900">{item.factor}</h4>
            <div className="text-xs text-slate-500">
              <strong>Affected Categories:</strong>
              <div className="flex flex-wrap gap-1 mt-1">
                {item.affected_categories.map((c: string) => (
                  <span key={c} className="bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded text-[11px]">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Inventory Turnover Alerts */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          Inventory Turnover & Stockout Prevention Alerts
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {report.inventory_turnover_alerts.map((alert: any, idx: number) => (
            <div
              key={idx}
              className={`p-4 rounded-xl border flex items-center justify-between text-xs ${
                alert.days_remaining < 7
                  ? "bg-amber-50 border-amber-200 text-amber-900"
                  : "bg-slate-50 border-slate-200 text-slate-800"
              }`}
            >
              <div>
                <p className="font-bold text-sm">{alert.product}</p>
                <p className="text-slate-500 mt-0.5">
                  Stock: <strong className="text-slate-800">{alert.stock} units</strong> | Est. Days Remaining:{" "}
                  <strong className="text-slate-800">{alert.days_remaining} days</strong>
                </p>
              </div>

              <span className="font-bold px-3 py-1.5 rounded-lg bg-white border shadow-subtle">
                {alert.action}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
