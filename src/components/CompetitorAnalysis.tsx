"use client";

import React, { useState, useEffect } from "react";
import { Search, TrendingUp, DollarSign, Layers, ShieldCheck, AlertCircle, ArrowUpRight, ArrowDownRight } from "lucide-react";

export const CompetitorAnalysis: React.FC = () => {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/competitor-analysis")
      .then((res) => res.json())
      .then((resData) => setData(resData.competitor_matrix || []))
      .catch(() => {
        setData([
          { product_id: "prod-1", product_name: "Wireless Noise-Canceling Headphones", category: "Electronics", our_price: 199.99, competitor_name: "TechGiant Store", competitor_price: 189.99, price_difference: -10.0, difference_pct: -5.0, market_position: "Premium (Risk of losing price-sensitive shoppers)" },
          { product_id: "prod-2", product_name: "Smart Fitness Watch Ultra", category: "Wearables", our_price: 249.5, competitor_name: "FitLife Direct", competitor_price: 259.99, price_difference: 10.49, difference_pct: 4.2, market_position: "Underpriced (Opportunity to raise price)" },
          { product_id: "prod-3", product_name: "Ergonomic Mesh Office Chair", category: "Furniture", our_price: 329.0, competitor_name: "OfficeDepot Hub", competitor_price: 349.0, price_difference: 20.0, difference_pct: 6.1, market_position: "Underpriced (Opportunity to raise price)" },
          { product_id: "prod-4", product_name: "Mechanical Gaming Keyboard RGB", category: "Gaming", our_price: 89.99, competitor_name: "CyberGear World", competitor_price: 79.99, price_difference: -10.0, difference_pct: -11.1, market_position: "Premium (Risk of losing price-sensitive shoppers)" },
          { product_id: "prod-5", product_name: "Ultra-Wide 4K Monitor 34-inch", category: "Electronics", our_price: 499.99, competitor_name: "VisionMarket", competitor_price: 529.99, price_difference: 30.0, difference_pct: 6.0, market_position: "Underpriced (Opportunity to raise price)" },
          { product_id: "prod-6", product_name: "Portable Espresso Coffee Maker", category: "Home Appliances", our_price: 74.5, competitor_name: "KitchenBoutique", competitor_price: 69.99, price_difference: -4.51, difference_pct: -6.1, market_position: "Premium (Risk of losing price-sensitive shoppers)" }
        ]);
      });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold mb-2">
          <Search className="w-3.5 h-3.5" />
          Competitor Price Intelligence & Market Comparison
        </div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          Real-Time Competitor Price Monitoring
        </h2>
        <p className="text-slate-500 text-xs mt-1">
          Automated web scraping & search agent tracking across key rival retailers.
        </p>
      </div>

      {/* Competitor Matrix Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-bold uppercase border-b border-slate-200">
              <tr>
                <th className="px-6 py-4">Product Name</th>
                <th className="px-6 py-4">Our Price</th>
                <th className="px-6 py-4">Competitor & Retailer</th>
                <th className="px-6 py-4">Competitor Price</th>
                <th className="px-6 py-4">Price Difference</th>
                <th className="px-6 py-4">Market Positioning</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((item) => (
                <tr key={item.product_id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <p className="font-bold text-slate-900">{item.product_name}</p>
                    <span className="text-[10px] text-slate-400 font-semibold">{item.category}</span>
                  </td>

                  <td className="px-6 py-4 font-mono font-bold text-slate-900">
                    ${item.our_price.toFixed(2)}
                  </td>

                  <td className="px-6 py-4 font-medium text-slate-700">
                    {item.competitor_name}
                  </td>

                  <td className="px-6 py-4 font-mono font-bold text-slate-900">
                    ${item.competitor_price.toFixed(2)}
                  </td>

                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1 font-mono font-bold px-2 py-0.5 rounded text-xs ${
                        item.price_difference > 0
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-rose-50 text-rose-700 border border-rose-200"
                      }`}
                    >
                      {item.price_difference > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      ${Math.abs(item.price_difference).toFixed(2)} ({item.difference_pct}%)
                    </span>
                  </td>

                  <td className="px-6 py-4">
                    <span
                      className={`px-3 py-1 rounded-full text-[11px] font-bold border ${
                        item.market_position.includes("Underpriced")
                          ? "bg-emerald-100 text-emerald-800 border-emerald-200"
                          : "bg-amber-100 text-amber-800 border-amber-200"
                      }`}
                    >
                      {item.market_position}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
