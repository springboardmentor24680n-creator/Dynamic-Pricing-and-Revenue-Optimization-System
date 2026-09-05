import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function AIRecommendation({ products, salesInfo, userRole }) {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [competitorPrice, setCompetitorPrice] = useState("");
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [forecastData, setForecastData] = useState(null);
  const [forecastTab, setForecastTab] = useState("short_term");

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const getMainReason = (report) => {
    if (!report) return "";
    const recPrice = report.recommended_price || 0;
    const minPrice = report.minimum_allowed_price || 0;
    const compPrice = report.competitor_price;
    const supply = report.days_of_supply || 0;
    const trend = report.demand_trend || "";

    if (Math.abs(recPrice - minPrice) < 0.1) {
      return "Minimum margin sets the lowest safe price.";
    }
    if (supply > 30 && compPrice !== null && compPrice !== undefined && compPrice > 0 && Math.abs(recPrice - Math.max(compPrice, minPrice)) < 0.1) {
      return "Competitor pricing is putting downward pressure on the recommended price.";
    }
    if (supply > 30) {
      return "High inventory is encouraging a lower price to increase sales.";
    }
    if (trend === "Increasing" || trend === "Seasonal") {
      return "Strong demand allows the system to consider a higher price.";
    }
    return "The price is selected to balance demand, revenue, and profit.";
  };

  const getDynamicExplanation = (report) => {
    if (!report) return "";
    const recPrice = report.recommended_price || 0;
    const minPrice = report.minimum_allowed_price || 0;
    const compPrice = report.competitor_price;
    const supply = report.days_of_supply || 0;

    let parts = [];
    if (supply > 30) {
      parts.push("high inventory");
    }
    if (compPrice !== null && compPrice !== undefined && compPrice > 0 && compPrice < report.current_price) {
      parts.push("competitor pressure");
    }

    const factorsText = parts.length > 0 ? parts.join(" and ") + " are pushing the price lower" : "market demand and price optimization determine the target price";

    if (Math.abs(recPrice - minPrice) < 0.1) {
      return `${factorsText.charAt(0).toUpperCase() + factorsText.slice(1)}. The minimum margin rule prevents the price from going below ${formatCurrency(minPrice)}.`;
    }
    if (supply > 30 && compPrice !== null && compPrice !== undefined && compPrice > 0 && Math.abs(recPrice - Math.max(compPrice, minPrice)) < 0.1) {
      return `${factorsText.charAt(0).toUpperCase() + factorsText.slice(1)}. The recommended price matches the competitor price cap of ${formatCurrency(compPrice)}.`;
    }
    return `The price of ${formatCurrency(recPrice)} is selected to balance expected demand, revenue, and profit margin.`;
  };

  const getColorClasses = (color) => {
    switch (color) {
      case "green":
        return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/40";
      case "red":
        return "bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-400 border border-rose-200 dark:border-rose-900/40";
      case "yellow":
        return "bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-400 border border-amber-250 dark:border-amber-900/40";
      case "blue":
      default:
        return "bg-sky-50 text-sky-700 dark:bg-sky-950/20 dark:text-sky-400 border border-sky-200 dark:border-sky-900/40";
    }
  };

  const getFactorsList = (report) => {
    if (!report) return [];
    
    const recPrice = report.recommended_price || 0;
    const minPrice = report.minimum_allowed_price || 0;
    const compPrice = report.competitor_price;
    const currPrice = report.current_price || 0;
    const supply = report.days_of_supply || 0;
    const elasticity = report.price_elasticity || 0;
    const trend = report.demand_trend || "";
    const seasonality = report.seasonality || "";
    const confidence = report.forecast_confidence || 0;
    const stock = report.current_stock || 0;
    const cost = report.cost_price || 0;
    const histSales = report.historical_sales || 0;
    const dailyVel = report.daily_sales_velocity || 0;

    const list = [];

    // 1. Expected Demand
    list.push({
      name: "Expected Demand",
      value: `${report.expected_demand.toFixed(1)} units`,
      impact: "🟢 Supports sales volume",
      color: "green"
    });

    // 2. Competitor Price
    let compValue = "—";
    let compImpact = "⚪ No competitor detected";
    let compColor = "blue";
    if (compPrice !== null && compPrice !== undefined && compPrice > 0) {
      compValue = formatCurrency(compPrice);
      if (compPrice < currPrice) {
        compImpact = "🔴 Pushes price down";
        compColor = "red";
      } else {
        compImpact = "🟢 Supports higher price";
        compColor = "green";
      }
    }
    list.push({
      name: "Competitor Price",
      value: compValue,
      impact: compImpact,
      color: compColor
    });

    // 3. Minimum Safe Price (Minimum Margin)
    list.push({
      name: "Minimum Margin",
      value: formatCurrency(minPrice),
      impact: "🛡️ Protects profit",
      color: "yellow"
    });

    // 4. Inventory
    const isSupplyNumeric = typeof supply === 'number';
    let invValue = isSupplyNumeric ? `${stock} units (${supply.toFixed(1)} days)` : `${stock} units`;
    let supplyDisplay = isSupplyNumeric ? `${supply.toFixed(1)} days` : supply;
    let invImpact = "🟢 Healthy inventory level";
    let invColor = "green";
    if (isSupplyNumeric) {
      if (supply > 30) {
        invImpact = "🔴 Pushes price down";
        invColor = "red";
      } else if (supply < 10) {
        invImpact = "🟢 Supports higher price";
        invColor = "green";
      }
    } else {
      invImpact = "⚪ Insufficient sales history";
      invColor = "blue";
    }
    list.push({
      name: "Inventory",
      value: invValue,
      impact: invImpact,
      color: invColor
    });

    // 5. Price Sensitivity
    let sensValue = "Standard";
    let sensImpact = "🟢 Allows flexible pricing";
    let sensColor = "green";
    if (elasticity < -1.0) {
      sensValue = "High";
      sensImpact = "🔴 Limits price increases";
      sensColor = "red";
    }
    list.push({
      name: "Price Sensitivity",
      value: sensValue,
      impact: sensImpact,
      color: sensColor
    });

    // 6. Demand Trend
    let trendImpact = "🟢 Supports price stability";
    let trendColor = "green";
    if (trend === "Increasing" || trend === "Seasonal") {
      trendImpact = "🟢 Supports price increases";
      trendColor = "green";
    } else if (trend === "Decreasing") {
      trendImpact = "🔴 Pushes price down";
      trendColor = "red";
    }
    list.push({
      name: "Demand Trend",
      value: trend,
      impact: trendImpact,
      color: trendColor
    });

    // 7. Seasonality
    let seasImpact = "🟢 Normal pricing flexibility";
    let seasColor = "green";
    if (seasonality === "Strong" || seasonality === "High") {
      seasImpact = "🟢 High pricing flexibility";
      seasColor = "green";
    }
    list.push({
      name: "Seasonality",
      value: seasonality,
      impact: seasImpact,
      color: seasColor
    });

    // 8. Forecast Confidence
    list.push({
      name: "Forecast Confidence",
      value: confidence ? `${confidence.toFixed(2)}%` : "N/A",
      impact: confidence > 80 ? "🟢 Reliable prediction" : "⚪ Standard prediction",
      color: confidence > 80 ? "green" : "blue"
    });

    return list;
  };

  const renderBusinessImpact = (report) => {
    if (!report || !report.historical_sales || report.historical_sales <= 0) return null;

    const histSales = report.historical_sales;
    const histRev = report.historical_revenue || 0;
    const cost = report.cost_price || 0;
    const currPrice = report.current_price || 0;
    const expectedDemand = report.expected_demand || 0;
    const expectedRev = report.expected_revenue || 0;
    const expectedProfit = report.expected_profit || 0;

    const baselineProfit = (currPrice - cost) * histSales;
    const profitGain = expectedProfit - baselineProfit;
    const revGain = expectedRev - histRev;

    const formatPct = (val, base) => {
      if (!base || base === 0) return "0.0%";
      const pct = (val / base) * 100;
      return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
    };

    return (
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 text-left text-slate-900 dark:text-white shadow-sm space-y-4 animate-fade-in">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">Business Impact Analysis</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Comparing baseline historical performance (30-day period) with estimated optimization metrics under the recommended price.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Sales Volume */}
          <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Expected Sales Volume</span>
            <div className="flex justify-between items-end">
              <div>
                <span className="text-slate-500 text-[10px] block">Baseline</span>
                <span className="font-bold text-slate-700 dark:text-slate-300 text-sm">{histSales.toFixed(0)} units</span>
              </div>
              <div className="text-right">
                <span className="text-slate-500 text-[10px] block">AI Target</span>
                <span className="font-extrabold text-violet-600 dark:text-violet-400 text-base block">{expectedDemand.toFixed(1)} units</span>
              </div>
            </div>
            <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex justify-between text-xs">
              <span className="text-slate-500 text-[10px]">Volume Change</span>
              <span className={`font-bold ${expectedDemand - histSales >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {(expectedDemand - histSales).toFixed(1)} units ({formatPct(expectedDemand - histSales, histSales)})
              </span>
            </div>
          </div>

          {/* Revenue Impact */}
          <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Estimated Revenue</span>
            <div className="flex justify-between items-end">
              <div>
                <span className="text-slate-500 text-[10px] block">Baseline</span>
                <span className="font-bold text-slate-700 dark:text-slate-300 text-sm">{formatCurrency(histRev)}</span>
              </div>
              <div className="text-right">
                <span className="text-slate-500 text-[10px] block">AI Target</span>
                <span className="font-extrabold text-violet-600 dark:text-violet-400 text-base block">{formatCurrency(expectedRev)}</span>
              </div>
            </div>
            <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex justify-between text-xs">
              <span className="text-slate-500 text-[10px]">Revenue Gain</span>
              <span className={`font-bold ${revGain >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {formatCurrency(revGain)} ({formatPct(revGain, histRev)})
              </span>
            </div>
          </div>

          {/* Profit Impact */}
          <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Estimated Gross Profit</span>
            <div className="flex justify-between items-end">
              <div>
                <span className="text-slate-500 text-[10px] block">Baseline</span>
                <span className="font-bold text-slate-700 dark:text-slate-300 text-sm">{formatCurrency(baselineProfit)}</span>
              </div>
              <div className="text-right">
                <span className="text-slate-500 text-[10px] block">AI Target</span>
                <span className="font-extrabold text-violet-600 dark:text-violet-400 text-base block">{formatCurrency(expectedProfit)}</span>
              </div>
            </div>
            <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex justify-between text-xs">
              <span className="text-slate-500 text-[10px]">Profit Gain</span>
              <span className={`font-bold ${profitGain >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {formatCurrency(profitGain)} ({formatPct(profitGain, baselineProfit)})
              </span>
            </div>
          </div>
        </div>
      </section>
    );
  };

  const selectedProduct = products.find((p) => String(p.id) === String(selectedProductId));

  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      const firstProduct = products[0];
      const firstId = String(firstProduct.id);
      setSelectedProductId(firstId);
      setCompetitorPrice((firstProduct.current_price * 1.05).toFixed(2));
    }
  }, [products]);

  const handleProductChange = (e) => {
    const id = e.target.value;
    setSelectedProductId(id);
    const product = products.find((p) => String(p.id) === String(id));
    if (product) {
      setCompetitorPrice((product.current_price * 1.05).toFixed(2));
    }
    setRecommendation(null);
    setForecastData(null);
    setError("");
  };

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    if (!selectedProduct) return;

    setLoading(true);
    setError("");
    setRecommendation(null);
    setForecastData(null);

    let salesCount = 100;
    let revenueSum = 100 * (selectedProduct.current_price || 1.0);
    if (salesInfo && salesInfo.sample) {
      const productSales = salesInfo.sample.filter(
        (s) => s.product_name === selectedProduct.name || String(s.product_id) === String(selectedProduct.id)
      );
      const units = productSales.reduce((acc, s) => acc + (s.quantity_sold || s.units_sold || 0), 0);
      const rev = productSales.reduce((acc, s) => acc + (s.revenue || 0), 0);
      if (units > 0) salesCount = units;
      if (rev > 0) revenueSum = rev;
    }

    try {
      const token = localStorage.getItem("token");
      
      const [recRes, forecastRes] = await Promise.all([
        axios.get(`${API}/api/ai/recommend-price`, {
          params: {
            stockcode: String(selectedProduct.id),
            current_price: selectedProduct.current_price,
            current_inventory: selectedProduct.stock || 50,
            historical_sales: salesCount,
            historical_revenue: revenueSum,
            quantity: 10,
            revenue: revenueSum,
            competitor_price: competitorPrice ? Number(competitorPrice) : null
          },
        }),
        axios.get(`${API}/api/forecast/${selectedProduct.id}`, {
          params: {
            competitor_price: competitorPrice ? Number(competitorPrice) : null
          },
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
      ]);

      if (recRes.data && recRes.data.status === "success") {
        setRecommendation(recRes.data.recommendation);
      } else {
        setError("Invalid response format received from pricing service.");
      }

      if (forecastRes.data) {
        setForecastData(forecastRes.data);
      }
    } catch (err) {
      console.error("Error loading price recommendation or demand forecast:", err);
      setError(
        err.response?.data?.detail || "Failed to load recommendation and forecast telemetry from AI module."
      );
    } finally {
      setLoading(false);
    }
  };

  const getRecommendationBadge = (recType) => {
    const label = recType || "Maintain Price";
    if (label.includes("Increase")) {
      return (
        <span className="inline-flex items-center px-4 py-1.5 rounded-full text-sm font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
          <span className="w-2 h-2 mr-2 rounded-full bg-emerald-500 animate-pulse"></span>
          {label}
        </span>
      );
    }
    if (label.includes("Decrease")) {
      return (
        <span className="inline-flex items-center px-4 py-1.5 rounded-full text-sm font-semibold bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50">
          <span className="w-2 h-2 mr-2 rounded-full bg-rose-500 animate-pulse"></span>
          {label}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-4 py-1.5 rounded-full text-sm font-semibold bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50">
        <span className="w-2 h-2 mr-2 rounded-full bg-amber-500"></span>
        {label}
      </span>
    );
  };

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6 space-y-6">
      <header className="mb-6">
        <p className="text-sm font-semibold tracking-wider text-violet-600 dark:text-violet-400 uppercase">AI Dynamic Pricing</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">Pricing Recommendation Workspace</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">Professional pricing intelligence tool powered by Prophet demand forecasts and profit maximization models.</p>
      </header>

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400 text-left">
          <h4 className="font-bold">Error</h4>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Product Selector & Parameters */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Product Parameters</h3>

            <div>
              <label htmlFor="prod-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Product selector</label>
              <select
                id="prod-select"
                value={selectedProductId}
                onChange={handleProductChange}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-medium text-sm cursor-pointer"
              >
                {products && products.length > 0 ? (
                  products.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))
                ) : (
                  <option value="">No products available</option>
                )}
              </select>
            </div>

            <div>
              <label htmlFor="competitor-price" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Competitor Price (₹)</label>
              <input
                id="competitor-price"
                type="number"
                step="0.01"
                min="0"
                value={competitorPrice}
                onChange={(e) => setCompetitorPrice(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-medium text-sm"
                required
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading || !selectedProductId}
              className="w-full flex items-center justify-center gap-2 py-3.5 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-400 dark:disabled:text-slate-600 text-white rounded-xl font-bold transition shadow-md shadow-violet-500/10 cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Calculating...</span>
                </>
              ) : (
                <span>Generate AI Price Recommendation</span>
              )}
            </button>
          </div>

          {/* Seasonal Context Card */}
          {recommendation && (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4 text-left">
              <div className="border-b border-slate-100 dark:border-slate-800 pb-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Seasonal Context</span>
              </div>
              <div className="space-y-3 text-xs font-semibold text-slate-650 dark:text-slate-400">
                <div className="flex justify-between">
                  <span>Seasonal Status:</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] ${
                    recommendation.pricing_analysis_report.seasonality === "Strong"
                      ? "bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-400 border border-rose-200"
                      : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400 border border-emerald-200"
                  }`}>
                    {recommendation.pricing_analysis_report.seasonality === "N/A" ? "Stable" : "Active Season"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Demand Direction:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {recommendation.pricing_analysis_report.demand_trend || "Stable"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Seasonality Strength:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {recommendation.pricing_analysis_report.seasonality || "Moderate"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Peak Period:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {recommendation.pricing_analysis_report.peak_period || "N/A"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Low Period:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {recommendation.pricing_analysis_report.low_period || "N/A"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Key Business Metrics & Outputs */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
            {!recommendation ? (
              <>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Business Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Current Price</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {selectedProduct ? formatCurrency(selectedProduct.current_price) : "₹0.00"}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Competitor Price</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {competitorPrice ? formatCurrency(Number(competitorPrice)) : "—"}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Cost Price</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {selectedProduct ? formatCurrency(selectedProduct.cost_price) : "₹0.00"}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Current Stock</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {selectedProduct ? `${selectedProduct.stock} units` : "—"}
                    </span>
                  </div>
                </div>
                <div className="text-center py-8 text-slate-550 dark:text-slate-400 text-sm">
                  Click "Generate AI Price Recommendation" to run the optimization model.
                </div>
              </>
            ) : (
              <>
                <div className="bg-violet-50/50 dark:bg-violet-950/20 p-6 rounded-2xl border border-violet-100 dark:border-violet-900/30 text-center space-y-2">
                  <span className="text-sm font-bold text-violet-600 dark:text-violet-400 uppercase tracking-wider block">AI Recommended Price</span>
                  <span className="text-4xl font-extrabold text-violet-700 dark:text-violet-300 block">
                    {formatCurrency(recommendation.pricing_analysis_report.recommended_price)}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Current Price</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {formatCurrency(recommendation.pricing_analysis_report.current_price)}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-550 dark:text-slate-400 block">Competitor Price</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {recommendation.pricing_analysis_report.competitor_price ? formatCurrency(recommendation.pricing_analysis_report.competitor_price) : "—"}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Expected Demand</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {recommendation.pricing_analysis_report.expected_demand.toFixed(1)} units
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Expected Revenue</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {formatCurrency(recommendation.pricing_analysis_report.expected_revenue)}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Expected Profit</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {formatCurrency(recommendation.pricing_analysis_report.expected_profit)}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">Forecast Confidence</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 block">
                      {recommendation.pricing_analysis_report.forecast_confidence ? `${recommendation.pricing_analysis_report.forecast_confidence.toFixed(2)}%` : "N/A"}
                    </span>
                  </div>
                </div>

                {/* Final Pricing Decision Card */}
                <div className="bg-violet-50/30 dark:bg-violet-950/10 p-5 rounded-2xl border border-violet-100 dark:border-violet-900/30 space-y-3 mt-4 text-left">
                  <h4 className="text-sm font-bold text-violet-750 dark:text-violet-400 uppercase tracking-wider block">Final Pricing Decision</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-slate-800 dark:text-slate-200">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block">Current Price</span>
                      <span className="text-lg font-extrabold">{formatCurrency(recommendation.pricing_analysis_report.current_price)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block">AI Recommended Price</span>
                      <span className="text-lg font-extrabold text-violet-600 dark:text-violet-400">{formatCurrency(recommendation.pricing_analysis_report.recommended_price)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block">Price Difference</span>
                      <span className={`text-lg font-extrabold ${recommendation.pricing_analysis_report.recommended_price - recommendation.pricing_analysis_report.current_price >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                        {recommendation.pricing_analysis_report.recommended_price - recommendation.pricing_analysis_report.current_price >= 0 ? "+" : ""}
                        {formatCurrency(recommendation.pricing_analysis_report.recommended_price - recommendation.pricing_analysis_report.current_price)}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block">Percentage Change</span>
                      <span className={`text-lg font-extrabold ${recommendation.pricing_analysis_report.recommended_price - recommendation.pricing_analysis_report.current_price >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                        {recommendation.pricing_analysis_report.recommended_price - recommendation.pricing_analysis_report.current_price >= 0 ? "+" : ""}
                        {((recommendation.pricing_analysis_report.recommended_price - recommendation.pricing_analysis_report.current_price) / (recommendation.pricing_analysis_report.current_price || 0.01) * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Why did AI recommend this price? Card */}
      {recommendation && (
        <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 text-left text-slate-900 dark:text-white shadow-sm relative overflow-hidden space-y-6 animate-fade-in">
          <div className="absolute top-0 right-0 w-60 h-60 bg-violet-600/10 rounded-full filter blur-3xl -translate-y-1/2 translate-x-1/2"></div>
          
          <div className="relative space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">Why This Price?</h2>
            
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-50 dark:bg-slate-950/40 p-5 rounded-2xl border border-slate-100 dark:border-slate-850">
              <div className="space-y-1">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">AI Recommended Price</span>
                <span className="text-3xl font-extrabold text-violet-600 dark:text-violet-400 block">
                  {formatCurrency(recommendation.pricing_analysis_report.recommended_price)}
                </span>
              </div>
              
              <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/50 dark:bg-amber-950/20">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 block mb-1">Main Reason For This Price</span>
                <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  {getMainReason(recommendation.pricing_analysis_report)}
                </p>
              </div>
            </div>

            <p className="text-sm text-slate-750 dark:text-slate-350 leading-relaxed font-medium bg-slate-50/50 dark:bg-slate-900 p-4 rounded-xl border border-slate-100 dark:border-slate-850">
              {getDynamicExplanation(recommendation.pricing_analysis_report)}
            </p>
          </div>

          <div className="relative border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-50/20 dark:bg-slate-950/40">
            <table className="w-full text-sm text-left text-slate-700 dark:text-slate-300">
              <thead className="text-xs uppercase bg-slate-50 dark:bg-slate-950 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-6 py-3.5 font-semibold">Factor</th>
                  <th className="px-6 py-3.5 font-semibold">Value</th>
                  <th className="px-6 py-3.5 font-semibold">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-750 dark:text-slate-350 bg-white dark:bg-slate-900">
                {getFactorsList(recommendation.pricing_analysis_report).map((factor, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    <td className="px-6 py-3.5 font-semibold text-slate-900 dark:text-white">
                      {factor.name}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${getColorClasses(factor.color)}`}>
                        {factor.value}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-xs text-slate-650 dark:text-slate-400 leading-relaxed font-semibold">
                      {factor.impact}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Days of Supply Calculation details breakdown */}
          <div className="bg-slate-50 dark:bg-slate-950/40 p-4 rounded-xl border border-slate-205 dark:border-slate-800 text-xs space-y-2 mt-4 text-left">
            <span className="font-bold text-slate-750 dark:text-slate-300 block">📊 Days of Supply Calculation:</span>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-slate-600 dark:text-slate-400">
              <div>
                <span className="block font-semibold">Historical Sales:</span>
                <span>{recommendation.pricing_analysis_report.historical_sales.toFixed(0)} units / 30 days</span>
              </div>
              <div>
                <span className="block font-semibold">Daily Sales Velocity:</span>
                <span>
                  {typeof recommendation.pricing_analysis_report.daily_sales_velocity === 'number' 
                    ? `${recommendation.pricing_analysis_report.daily_sales_velocity.toFixed(4)} units/day` 
                    : recommendation.pricing_analysis_report.daily_sales_velocity}
                </span>
              </div>
              <div>
                <span className="block font-semibold">Inventory:</span>
                <span>{recommendation.pricing_analysis_report.current_inventory} units</span>
              </div>
              <div>
                <span className="block font-semibold text-slate-800 dark:text-slate-200">Days of Supply:</span>
                <span className="font-bold text-violet-600 dark:text-violet-400">
                  {typeof recommendation.pricing_analysis_report.days_of_supply === 'number'
                    ? `${recommendation.pricing_analysis_report.days_of_supply.toFixed(1)} days`
                    : recommendation.pricing_analysis_report.days_of_supply}
                </span>
              </div>
            </div>
            <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-slate-500 italic">
              Formula: Days of Supply = Inventory ÷ Daily Sales Velocity
            </div>
          </div>
        </section>
      )}

      {recommendation && renderBusinessImpact(recommendation.pricing_analysis_report)}

      {/* Demand Forecast Section */}
      {forecastData && (
        <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 text-left text-slate-900 dark:text-white shadow-sm space-y-6 animate-fade-in relative overflow-hidden">
          <div className="absolute top-0 right-0 w-60 h-60 bg-emerald-600/5 rounded-full filter blur-3xl -translate-y-1/2 translate-x-1/2"></div>
          
          <div className="border-b border-slate-100 dark:border-slate-800 pb-4">
            <p className="text-xs font-semibold tracking-wider text-emerald-600 dark:text-emerald-400 uppercase">Projections</p>
            <h2 className="text-xl font-extrabold mt-1">Multi-Horizon Demand Forecast</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Compare short-term, mid-term, and long-term volume predictions powered by LightGBM regressors and Prophet seasonality models.</p>
          </div>

          {/* Tab Selector */}
          <div className="flex border-b border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setForecastTab("short_term")}
              className={`flex-1 pb-3 text-sm font-bold border-b-2 text-center transition cursor-pointer ${forecastTab === "short_term" ? "border-emerald-500 text-emerald-600 dark:text-emerald-400" : "border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"}`}
            >
              Short-Term
              <span className="block text-[10px] font-medium text-slate-400">7–30 Days</span>
            </button>
            <button
              onClick={() => setForecastTab("mid_term")}
              className={`flex-1 pb-3 text-sm font-bold border-b-2 text-center transition cursor-pointer ${forecastTab === "mid_term" ? "border-emerald-500 text-emerald-600 dark:text-emerald-400" : "border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"}`}
            >
              Mid-Term
              <span className="block text-[10px] font-medium text-slate-400">31–90 Days</span>
            </button>
            <button
              onClick={() => setForecastTab("long_term")}
              className={`flex-1 pb-3 text-sm font-bold border-b-2 text-center transition cursor-pointer ${forecastTab === "long_term" ? "border-emerald-500 text-emerald-600 dark:text-emerald-400" : "border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"}`}
            >
              Long-Term
              <span className="block text-[10px] font-medium text-slate-400">91–365 Days</span>
            </button>
          </div>

          {/* Forecast Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Forecast Demand</span>
              <span className="text-xl font-extrabold text-slate-800 dark:text-slate-255 mt-1 block">
                {forecastData[forecastTab].expected_demand !== null 
                  ? `${forecastData[forecastTab].expected_demand.toFixed(1)} units`
                  : "N/A"}
              </span>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Avg Daily Demand</span>
              <span className="text-xl font-extrabold text-slate-800 dark:text-slate-255 mt-1 block">
                {forecastData[forecastTab].average_daily_demand !== null 
                  ? `${forecastData[forecastTab].average_daily_demand.toFixed(2)} units/day`
                  : "N/A"}
              </span>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Forecast Confidence</span>
              <span className="text-xl font-extrabold text-slate-800 dark:text-slate-255 mt-1 block">
                {forecastData[forecastTab].confidence !== null 
                  ? `${forecastData[forecastTab].confidence.toFixed(1)}%`
                  : "N/A"}
              </span>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Trend Classification</span>
              <span className="text-xl font-extrabold text-slate-800 dark:text-slate-255 mt-1 block">
                {forecastData[forecastTab].trend}
              </span>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800/50 space-y-1 col-span-2 md:col-span-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Model In Use</span>
              <span className="text-xl font-extrabold text-emerald-600 dark:text-emerald-450 mt-1 block">
                {forecastData[forecastTab].model}
              </span>
            </div>
          </div>

          {/* Planning & Constraints Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-left">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Inventory Status</span>
              <span className="text-sm font-extrabold text-slate-800 dark:text-slate-250 mt-1 block">{forecastData.inventory_status}</span>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Stockout Risk</span>
              <span className={`text-sm font-extrabold mt-1 block ${forecastData.stockout_risk ? "text-rose-600 dark:text-rose-450" : "text-emerald-600 dark:text-emerald-450"}`}>
                {forecastData.stockout_risk ? "⚠️ Yes (High)" : "🟢 No Risk"}
              </span>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Pricing Impact</span>
              <span className="text-sm font-extrabold text-slate-800 dark:text-slate-250 mt-1 block">
                {forecastData.pricing_signal.includes("margin") ? "Optimized Margin" : "Base Pricing"}
              </span>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Generated At</span>
              <span className="text-[11px] text-slate-500 dark:text-slate-450 mt-1 block">
                {new Date(forecastData.generated_at).toLocaleString()}
              </span>
            </div>
          </div>

          {/* Why this forecast? explanation card */}
          <div className="bg-slate-50 dark:bg-slate-950/40 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4 text-left">
            <h3 className="text-sm font-bold text-slate-750 dark:text-slate-300 uppercase tracking-wider block">❓ Why This Forecast?</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 p-4 rounded-xl space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300">📈 Trend Classification</span>
                <p className="text-slate-500 dark:text-slate-450">
                  Model detected general trend: <span className="font-bold text-emerald-600 dark:text-emerald-450">{forecastData[forecastTab].trend}</span>
                </p>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 p-4 rounded-xl space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300">🏷️ Pricing Signal (Model Input)</span>
                <p className="text-slate-500 dark:text-slate-450">{forecastData.pricing_signal}</p>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 p-4 rounded-xl space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300">⚔️ Competitor & Market Signal (Model Input)</span>
                <p className="text-slate-500 dark:text-slate-450">{forecastData.competitor_signal}</p>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 p-4 rounded-xl space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300">🍂 Seasonal Factor (Model Input)</span>
                <p className="text-slate-500 dark:text-slate-450">
                  Active monthly seasonal index: <span className="font-bold text-violet-600 dark:text-violet-400">{forecastData.seasonal_factor}x</span> of baseline demand.
                </p>
              </div>
            </div>
          </div>

          {/* Render simple interactive SVG line chart */}
          {forecastData[forecastTab].forecast && forecastData[forecastTab].forecast.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block text-left">📈 Demand Projection Curve (Units/Day)</span>
              <div className="bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 flex flex-col items-center justify-center">
                {(() => {
                  const forecastPoints = forecastData[forecastTab].forecast;
                  const sampleStep = Math.max(1, Math.floor(forecastPoints.length / 10));
                  const sampledForecast = forecastPoints.filter((_, idx) => idx % sampleStep === 0).slice(0, 10);
                  
                  // Construct historical points
                  const histSalesPoints = salesInfo?.sample
                    ?.filter((s) => s.product_name === selectedProduct?.name || String(s.product_id) === String(selectedProduct?.id))
                    ?.slice(-4) || [];
                  const histData = histSalesPoints.map((s, idx) => ({
                    date: s.sales_date || `Day -${histSalesPoints.length - idx}`,
                    value: (s.quantity_sold || s.units_sold || 0) / 30.0
                  }));
                  // Fallback historical values if empty
                  if (histData.length === 0) {
                    const fallbackVel = (selectedProduct?.stock || 30) / 30.0;
                    histData.push({ date: "Day -3", value: fallbackVel * 0.9 });
                    histData.push({ date: "Day -2", value: fallbackVel * 0.95 });
                    histData.push({ date: "Day -1", value: fallbackVel });
                  }

                  const allPoints = [...histData, ...sampledForecast];
                  const maxVal = Math.max(0.1, ...allPoints.map(p => p.value)) * 1.25;

                  // Plot Coordinates
                  const width = 600;
                  const height = 180;
                  const paddingLeft = 40;
                  const paddingRight = 20;
                  const paddingTop = 20;
                  const paddingBottom = 30;

                  const chartWidth = width - paddingLeft - paddingRight;
                  const chartHeight = height - paddingTop - paddingBottom;

                  const getX = (idx) => paddingLeft + (idx / (allPoints.length - 1)) * chartWidth;
                  const getY = (val) => height - paddingBottom - (val / maxVal) * chartHeight;

                  // Build paths
                  let histPath = "";
                  let forecastPath = "";

                  histData.forEach((p, idx) => {
                    const x = getX(idx);
                    const y = getY(p.value);
                    if (idx === 0) histPath += `M ${x} ${y}`;
                    else histPath += ` L ${x} ${y}`;
                  });

                  sampledForecast.forEach((p, idx) => {
                    const x = getX(histData.length + idx);
                    const y = getY(p.value);
                    if (idx === 0) {
                      const prevX = getX(histData.length - 1);
                      const prevY = getY(histData[histData.length - 1].value);
                      forecastPath += `M ${prevX} ${prevY} L ${x} ${y}`;
                    } else {
                      forecastPath += ` L ${x} ${y}`;
                    }
                  });

                  return (
                    <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-2xl h-auto text-slate-500 dark:text-slate-400 font-sans">
                      <line x1={paddingLeft} y1={getY(0)} x2={width - paddingRight} y2={getY(0)} stroke="currentColor" strokeWidth="1" strokeOpacity="0.15" />
                      <line x1={paddingLeft} y1={getY(maxVal / 2)} x2={width - paddingRight} y2={getY(maxVal / 2)} stroke="currentColor" strokeWidth="1" strokeOpacity="0.08" strokeDasharray="3 3" />
                      <line x1={paddingLeft} y1={getY(maxVal)} x2={width - paddingRight} y2={getY(maxVal)} stroke="currentColor" strokeWidth="1" strokeOpacity="0.08" strokeDasharray="3 3" />
                      
                      <text x={paddingLeft - 8} y={getY(0) + 3} textAnchor="end" className="text-[9px] fill-current">{0}</text>
                      <text x={paddingLeft - 8} y={getY(maxVal / 2) + 3} textAnchor="end" className="text-[9px] fill-current">{(maxVal / 2).toFixed(1)}</text>
                      <text x={paddingLeft - 8} y={getY(maxVal) + 3} textAnchor="end" className="text-[9px] fill-current">{maxVal.toFixed(1)}</text>

                      <line x1={getX(histData.length - 0.5)} y1={paddingTop} x2={getX(histData.length - 0.5)} y2={height - paddingBottom} stroke="#ef4444" strokeWidth="1.5" strokeOpacity="0.5" strokeDasharray="4 2" />
                      <text x={getX(histData.length - 0.5) - 4} y={paddingTop + 10} textAnchor="end" className="text-[8px] fill-rose-500 font-extrabold uppercase tracking-wide">History</text>
                      <text x={getX(histData.length - 0.5) + 4} y={paddingTop + 10} textAnchor="start" className="text-[8px] fill-violet-500 font-extrabold uppercase tracking-wide">Forecast</text>

                      <path d={histPath} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" />
                      {histData.map((p, idx) => (
                        <circle key={`h-${idx}`} cx={getX(idx)} cy={getY(p.value)} r="3.5" className="fill-blue-600 dark:fill-blue-400 stroke-white stroke-2" />
                      ))}

                      <path d={forecastPath} fill="none" stroke="#8b5cf6" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="4 3" />
                      {sampledForecast.map((p, idx) => (
                        <circle key={`f-${idx}`} cx={getX(histData.length + idx)} cy={getY(p.value)} r="3.5" className="fill-violet-600 dark:fill-violet-400 stroke-white stroke-2" />
                      ))}

                      {allPoints.map((p, idx) => {
                        if (idx !== 0 && idx !== histData.length - 1 && idx !== allPoints.length - 1) return null;
                        const labelText = p.date.includes("-") ? p.date.split("-").slice(1).join("/") : p.date;
                        return (
                          <text key={`l-${idx}`} x={getX(idx)} y={height - paddingBottom + 12} textAnchor="middle" className="text-[8px] fill-current font-semibold">{labelText}</text>
                        );
                      })}
                    </svg>
                  );
                })()}
              </div>
            </div>
          )}

          {/* Model Telemetry & Performance Details (Admin only) */}
          {userRole === "admin" && (
            <div className="bg-slate-50 dark:bg-slate-950/40 p-5 rounded-2xl border border-slate-205 dark:border-slate-800 space-y-3 text-left">
              <span className="font-extrabold text-xs text-slate-750 dark:text-slate-350 uppercase tracking-wider block">🛡️ Model Telemetry & Performance (Admin View)</span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Detailed error metrics evaluated on historical holdout validation splits to verify accuracy and avoid model drift.
              </p>
              <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900">
                <table className="w-full text-xs text-left text-slate-700 dark:text-slate-300">
                  <thead className="text-[10px] uppercase bg-slate-50 dark:bg-slate-950 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 font-bold">
                    <tr>
                      <th className="px-4 py-2.5">Model</th>
                      <th className="px-4 py-2.5">MAE (Mean Abs Error)</th>
                      <th className="px-4 py-2.5">RMSE (Root Mean Sq Error)</th>
                      <th className="px-4 py-2.5">R² Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                    <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">Prophet (Seasonality)</td>
                      <td className="px-4 py-2.5">{forecastData.metrics.prophet.mae.toFixed(4)}</td>
                      <td className="px-4 py-2.5">{forecastData.metrics.prophet.rmse.toFixed(4)}</td>
                      <td className="px-4 py-2.5">{forecastData.metrics.prophet.r2_score.toFixed(4)}</td>
                    </tr>
                    <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-4 py-2.5 font-bold text-slate-900 dark:text-white">LightGBM (Multi-Feature)</td>
                      <td className="px-4 py-2.5">{forecastData.metrics.lightgbm.mae.toFixed(4)}</td>
                      <td className="px-4 py-2.5">{forecastData.metrics.lightgbm.rmse.toFixed(4)}</td>
                      <td className="px-4 py-2.5">{forecastData.metrics.lightgbm.r2_score.toFixed(4)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
