"use client";

import React, { useState } from "react";
import { SlidersHorizontal, DollarSign, TrendingUp, Sparkles, Layers, ArrowUpRight } from "lucide-react";
import { Product } from "./ProductCatalog";

interface RevenueSimulatorProps {
  products: Product[];
}

export const RevenueSimulator: React.FC<RevenueSimulatorProps> = ({ products }) => {
  const [selectedProduct, setSelectedProduct] = useState<Product>(products[0] || {
    id: "prod-1",
    name: "Wireless Noise-Canceling Headphones",
    current_price: 199.99,
    cost_price: 110.0,
    competitor_price: 189.99,
    historical_sales_30d: 1250,
    elasticity_score: 1.45
  });

  const [priceAdjustPct, setPriceAdjustPct] = useState<number>(0);
  const [discountPct, setDiscountPct] = useState<number>(0);

  const curPrice = selectedProduct.current_price;
  const cost = selectedProduct.cost_price;
  const elasticity = selectedProduct.elasticity_score || 1.4;
  const baseDailyDemand = selectedProduct.historical_sales_30d / 30.0;

  const simulatedPrice = curPrice * (1 + priceAdjustPct / 100) * (1 - discountPct / 100);
  const priceRatio = curPrice / Math.max(simulatedPrice, 1);
  const simulatedDailyDemand = Math.max(1, Math.round(baseDailyDemand * Math.pow(priceRatio, elasticity)));

  const baselineDailyRev = baseDailyDemand * curPrice;
  const simulatedDailyRev = simulatedDailyDemand * simulatedPrice;

  const baselineDailyProfit = baseDailyDemand * (curPrice - cost);
  const simulatedDailyProfit = simulatedDailyDemand * (simulatedPrice - cost);

  const profitDiff = simulatedDailyProfit - baselineDailyProfit;
  const profitDiffPct = Number(((profitDiff / Math.max(baselineDailyProfit, 1)) * 100).toFixed(1));

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-xs font-bold mb-2">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Interactive Revenue & Margin Simulation Engine
        </div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          What-If Price Sensitivity & Discount Simulator
        </h2>
        <p className="text-slate-500 text-xs mt-1">
          Simulate price adjustments and promotional discounts to test projected revenue & margin outcomes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Controls Panel */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card space-y-6">
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-2">Select Product for Simulation</label>
            <select
              value={selectedProduct.id}
              onChange={(e) => {
                const found = products.find((p) => p.id === e.target.value);
                if (found) setSelectedProduct(found);
              }}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs font-semibold text-slate-800 focus:outline-none focus:border-brand-500"
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (${p.current_price})
                </option>
              ))}
            </select>
          </div>

          {/* Slider 1: Price Adjustment */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-slate-700">Base Price Adjustment</span>
              <span className="text-brand-600 font-mono">
                {priceAdjustPct >= 0 ? "+" : ""}{priceAdjustPct}%
              </span>
            </div>
            <input
              type="range"
              min="-25"
              max="35"
              value={priceAdjustPct}
              onChange={(e) => setPriceAdjustPct(Number(e.target.value))}
              className="w-full accent-brand-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-25% (Discount)</span>
              <span>0% (Current)</span>
              <span>+35% (Premium)</span>
            </div>
          </div>

          {/* Slider 2: Campaign Discount */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-slate-700">Promotional Campaign Discount</span>
              <span className="text-amber-600 font-mono">{discountPct}% OFF</span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              value={discountPct}
              onChange={(e) => setDiscountPct(Number(e.target.value))}
              className="w-full accent-amber-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>0%</span>
              <span>15%</span>
              <span>30%</span>
            </div>
          </div>
        </div>

        {/* Simulation Output Card */}
        <div className="lg:col-span-2 bg-gradient-to-tr from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-8 shadow-card flex flex-col justify-between space-y-6">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">Simulated Results</span>
              <span className="text-xs font-mono text-slate-300">
                Elasticity Score: {elasticity}
              </span>
            </div>

            <h3 className="text-2xl font-bold mt-2">{selectedProduct.name}</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                <span className="text-xs text-slate-400">Simulated Unit Price</span>
                <p className="text-2xl font-extrabold text-white mt-1">
                  ${simulatedPrice.toFixed(2)}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Base: ${curPrice.toFixed(2)}
                </p>
              </div>

              <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                <span className="text-xs text-slate-400">Projected Daily Volume</span>
                <p className="text-2xl font-extrabold text-white mt-1">
                  {simulatedDailyDemand} <span className="text-xs font-normal">units/day</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Base: {Math.round(baseDailyDemand)} units
                </p>
              </div>

              <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                <span className="text-xs text-slate-400">Projected Monthly Revenue</span>
                <p className="text-2xl font-extrabold text-emerald-400 mt-1">
                  ${Math.round(simulatedDailyRev * 30).toLocaleString()}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Base: ${Math.round(baselineDailyRev * 30).toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-slate-800/90 p-4 rounded-xl border border-slate-700 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Net Estimated Monthly Profit Difference</p>
              <p className={`text-2xl font-extrabold mt-0.5 ${profitDiff >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {profitDiff >= 0 ? "+" : ""}${Math.round(profitDiff * 30).toLocaleString()} / month ({profitDiffPct}%)
              </p>
            </div>

            <div className="text-right">
              <span className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold border border-emerald-500/30">
                {profitDiff >= 0 ? "Margin Enhancing Strategy" : "Margin Dilutive Strategy"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
