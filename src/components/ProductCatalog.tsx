"use client";

import React, { useState } from "react";
import { 
  Search, 
  Filter, 
  Layers, 
  Sparkles, 
  ArrowRight, 
  TrendingUp, 
  ShieldAlert, 
  Zap, 
  DollarSign, 
  BarChart, 
  CheckCircle2, 
  ChevronRight,
  RefreshCw
} from "lucide-react";

export interface Product {
  id: string;
  name: string;
  category: string;
  sku: string;
  current_price: number;
  cost_price: number;
  competitor_price: number;
  competitor_name: string;
  inventory: number;
  historical_sales_30d: number;
  rating: number;
  demand_trend: string;
  elasticity_score: number;
  discount_percentage: number;
  seasonality_factor: string;
  last_updated: string;
}

interface ProductCatalogProps {
  products: Product[];
  onPredictSingle: (product: Product) => void;
  onPredictAll: () => void;
}

export const ProductCatalog: React.FC<ProductCatalogProps> = ({
  products,
  onPredictSingle,
  onPredictAll
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const categories = ["All", ...Array.from(new Set(products.map((p) => p.category)))];

  const filteredProducts = products.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.sku.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "All" || p.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      {/* Top Header Controls with Both Prediction Buttons */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-xs font-semibold mb-1">
            <Layers className="w-3.5 h-3.5" />
            Product Catalog & Revenue Optimization
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Inventory & Price Intelligence Workbench
          </h2>
          <p className="text-slate-500 text-xs mt-0.5">
            Select an individual product for single prediction or launch autonomous batch price optimization across the full catalog.
          </p>
        </div>

        {/* Prediction Buttons - Button 1: Predict All Products */}
        <div className="flex items-center gap-3">
          <button
            onClick={onPredictAll}
            className="bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-700 hover:to-indigo-700 text-white font-bold px-5 py-3 rounded-xl transition-all shadow-md flex items-center gap-2 text-sm group"
          >
            <Sparkles className="w-4 h-4 text-amber-300 group-hover:rotate-12 transition-transform" />
            Predict All Products (Batch AI Run)
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search products by title or SKU..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-lg pl-10 pr-4 py-2 text-xs font-medium text-slate-800 focus:outline-none focus:border-brand-500 shadow-subtle"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-600">Category:</span>
          <div className="flex items-center gap-1 overflow-x-auto py-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  selectedCategory === cat
                    ? "bg-brand-600 text-white shadow-sm"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Product Catalog Grid / Table */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProducts.map((product) => {
          const margin = ((product.current_price - product.cost_price) / product.current_price) * 100;
          const compDiff = product.competitor_price - product.current_price;

          return (
            <div
              key={product.id}
              className="bg-white rounded-2xl border border-slate-200 shadow-card hover:shadow-card-hover transition-all p-6 flex flex-col justify-between space-y-4 group relative overflow-hidden"
            >
              {/* Product Badge */}
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-bold text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-0.5 rounded-full">
                    {product.category}
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    SKU: {product.sku}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 group-hover:text-brand-600 transition-colors line-clamp-1">
                  {product.name}
                </h3>
              </div>

              {/* Price & Competitor Comparison Block */}
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Catalog Price:</span>
                  <span className="text-base font-extrabold text-slate-900">
                    ${product.current_price.toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Cost Price:</span>
                  <span className="font-mono text-slate-700">${product.cost_price.toFixed(2)}</span>
                </div>

                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-200/80">
                  <span className="text-slate-500 font-medium">Competitor ({product.competitor_name}):</span>
                  <span className="font-semibold text-slate-800">
                    ${product.competitor_price.toFixed(2)}
                    {compDiff > 0 ? (
                      <span className="text-emerald-600 text-[10px] ml-1 font-bold">(+${compDiff.toFixed(2)})</span>
                    ) : compDiff < 0 ? (
                      <span className="text-rose-600 text-[10px] ml-1 font-bold">(-${Math.abs(compDiff).toFixed(2)})</span>
                    ) : null}
                  </span>
                </div>
              </div>

              {/* Key Product Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <p className="text-[10px] text-slate-400 font-medium">30d Demand Sales</p>
                  <p className="font-bold text-slate-800">{product.historical_sales_30d} units</p>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <p className="text-[10px] text-slate-400 font-medium">Current Stock</p>
                  <p className={`font-bold ${product.inventory < 100 ? "text-amber-600" : "text-emerald-700"}`}>
                    {product.inventory} units
                  </p>
                </div>
              </div>

              {/* Button 2: Predict Single Product Action */}
              <button
                onClick={() => onPredictSingle(product)}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-2.5 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-xs shadow-sm mt-2"
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Predict Single Product Price & Demand
                <ChevronRight className="w-4 h-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
