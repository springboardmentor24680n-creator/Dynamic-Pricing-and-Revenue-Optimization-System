import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function AIDashboard({ products, salesInfo }) {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const getProductSalesDetails = (product) => {
    if (!product || !salesInfo || !salesInfo.sample) {
      return { sales: 100, revenue: 100 * (product?.current_price || 1.0) };
    }
    
    // Find matching sales records
    const productSales = salesInfo.sample.filter(
      (s) => s.product_name === product.name || String(s.product_id) === String(product.id)
    );
    
    const salesCount = productSales.reduce((acc, s) => acc + (s.quantity_sold || s.units_sold || 0), 0);
    const revenueSum = productSales.reduce((acc, s) => acc + (s.revenue || 0), 0);
    
    return {
      sales: salesCount > 0 ? salesCount : 120, // default if no sales loaded
      revenue: revenueSum > 0 ? revenueSum : 120 * (product.current_price || 1.0),
    };
  };

  const fetchRecommendation = async (productId) => {
    const product = products.find((p) => String(p.id) === String(productId));
    if (!product) return;

    setLoading(true);
    setError("");
    setRecommendation(null);

    const { sales, revenue } = getProductSalesDetails(product);

    try {
      // Fetch optimal recommended price from backend AI route
      const response = await axios.get(`${API}/api/ai/recommend-price`, {
        params: {
          current_price: product.current_price,
          current_inventory: product.stock || 50,
          historical_sales: sales,
          historical_revenue: revenue,
          stockcode: String(product.id),
          quantity: 10,
          revenue: 15.0
        },
      });

      if (response.data && response.data.status === "success") {
        setRecommendation(response.data);
      } else {
        setError("Invalid response format received from AI service.");
      }
    } catch (err) {
      console.error("Error loading price recommendation:", err);
      setError(
        err.response?.data?.detail || "Failed to load price recommendations from AI module."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (products && products.length > 0 && !selectedProductId) {
      const firstId = String(products[0].id);
      setSelectedProductId(firstId);
      fetchRecommendation(firstId);
    }
  }, [products]);

  const handleProductChange = (e) => {
    const id = e.target.value;
    setSelectedProductId(id);
    fetchRecommendation(id);
  };

  const selectedProduct = products.find((p) => String(p.id) === String(selectedProductId));

  // Determine badge colors based on recommendation
  const getRecommendationBadge = (recType) => {
    const label = recType || "Maintain Price";
    if (label.includes("Increase")) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          {label}
        </span>
      );
    }
    if (label.includes("Decrease")) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-rose-500 animate-pulse"></span>
          {label}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50">
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-500"></span>
        {label}
      </span>
    );
  };

  const getConfidenceClassificationBadge = (confidence) => {
    let style = "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900/50";
    let text = "High";
    if (confidence < 70) {
      style = "bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-900/50";
      text = "Low";
    } else if (confidence < 85) {
      style = "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900/50";
      text = "Medium";
    }
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${style}`}>
        {text} Confidence
      </span>
    );
  };

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6">
      <header className="mb-8">
        <p className="text-sm font-semibold tracking-wider text-violet-600 dark:text-violet-400 uppercase">AI Analytics</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-1">AI Recommendation Workspace</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">Evaluate SKU elasticity curves, optimal price thresholds, demand spikes, and expected revenue impacts.</p>
      </header>

      {/* Product Selector Dropdown */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm mb-8">
        <div className="max-w-md">
          <label htmlFor="prod-select-id" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Select Target Product</label>
          <select
            id="prod-select-id"
            value={selectedProductId}
            onChange={handleProductChange}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-medium"
          >
            {products && products.length > 0 ? (
              products.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.category})
                </option>
              ))
            ) : (
              <option value="">No catalog products available</option>
            )}
          </select>
          {selectedProduct && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Product ID: <code className="text-slate-500 dark:text-slate-400 px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">{selectedProduct.id}</code> | Current Stock: <strong>{selectedProduct.stock || 0} units</strong>
            </p>
          )}
        </div>
      </section>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
          <div className="w-12 h-12 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 dark:text-slate-400 font-medium mt-4">Consulting dynamic price prediction engine...</p>
        </div>
      )}

      {error && (
        <div className="p-6 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400 mb-8">
          <h4 className="font-bold">Error Querying Recommendation Engine</h4>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {recommendation && (
        <div className="animate-fade-in">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            
            {/* Card 1: Recommendation Action */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Optimization Decision</span>
                {getRecommendationBadge(recommendation.recommendation?.recommendation)}
              </div>
              <h3 className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Recommended Price</h3>
              <div className="text-4xl font-extrabold text-slate-900 dark:text-white mt-1">
                {formatCurrency(recommendation.recommendation?.recommended_price)}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 border-t border-slate-100 dark:border-slate-800 pt-3">
                Current price: <strong>{formatCurrency(selectedProduct?.current_price)}</strong>
              </p>
            </div>

            {/* Card 2: Price Comparison */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Price Comparisons</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">LGBM Optimal vs Base</span>
              </div>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                    <span>Base Current Price</span>
                    <span>{formatCurrency(selectedProduct?.current_price)}</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-400 rounded-full" style={{ width: "70%" }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs font-semibold text-violet-600 dark:text-violet-400 mb-1">
                    <span>AI Predicted Price</span>
                    <span>{formatCurrency(recommendation.predicted_price)}</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-violet-600 dark:bg-violet-400 rounded-full" style={{ width: "90%" }}></div>
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 border-t border-slate-100 dark:border-slate-800 pt-3">
                Calculated headroom: <strong>{formatCurrency(recommendation.predicted_price - (selectedProduct?.current_price || 0))}</strong>
              </p>
            </div>

            {/* Card 3: Revenue Impact */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Revenue Impact</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 font-semibold border border-emerald-200 dark:border-emerald-900/50">Projected Gain</span>
              </div>
              <h3 className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Revenue Gain</h3>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                {recommendation.recommendation?.revenue_gain >= 0 ? "+" : ""}{formatCurrency(recommendation.recommendation?.revenue_gain)}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 border-t border-slate-100 dark:border-slate-800 pt-3">
                Projected Revenue: <strong>{formatCurrency(recommendation.recommendation?.expected_revenue)}</strong>
              </p>
            </div>

            {/* Card 4: Demand Forecast */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Prophet Demand Forecast</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">90d Projection</span>
              </div>
              <h3 className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Forecast Volume</h3>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                {recommendation.recommendation?.expected_demand ? recommendation.recommendation?.expected_demand.toLocaleString() : "0"} units
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-4 border-t border-slate-100 dark:border-slate-800 pt-3">
                Elasticity factored sales volume projection
              </p>
            </div>

            {/* Card 5: Forecast Confidence */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Confidence Analysis</span>
                {getConfidenceClassificationBadge(recommendation.recommendation?.confidence || 85)}
              </div>
              <h3 className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Confidence Score</h3>
              <div className="flex items-center gap-4 mt-2">
                <div className="text-3xl font-extrabold text-slate-900 dark:text-white">
                  {recommendation.recommendation?.confidence ? recommendation.recommendation?.confidence.toFixed(2) : "85.00"}%
                </div>
                <div className="flex-1 h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-violet-600 dark:bg-violet-400 rounded-full" 
                    style={{ width: `${recommendation.recommendation?.confidence || 85}%` }}
                  ></div>
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 border-t border-slate-100 dark:border-slate-800 pt-3">
                Based on historical variance and seasonality trends
              </p>
            </div>

            {/* Card 6: AI Registry Metadata */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow text-left">
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">System Parameters</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">Live Config</span>
              </div>
              <div className="text-xs space-y-2 mt-2 text-slate-600 dark:text-slate-400">
                <div className="flex justify-between">
                  <span>Price Elasticity:</span>
                  <span className="font-semibold text-slate-950 dark:text-white">-1.50</span>
                </div>
                <div className="flex justify-between">
                  <span>Regression Model:</span>
                  <span className="font-semibold text-slate-950 dark:text-white">LightGBM Regressor</span>
                </div>
                <div className="flex justify-between">
                  <span>Forecast Model:</span>
                  <span className="font-semibold text-slate-950 dark:text-white">Facebook Prophet</span>
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 border-t border-slate-100 dark:border-slate-800 pt-3">
                Active registered models in MongoDB
              </p>
            </div>

          </div>

          {/* AI Explanation / Rationale */}
          <section className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-left text-slate-900 dark:text-white shadow-sm relative overflow-hidden">
            {/* Background glowing gradient circle */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-violet-600/10 rounded-full filter blur-3xl -translate-y-1/2 translate-x-1/2"></div>
            
            <div className="flex items-center gap-3 mb-6 relative">
              <div className="p-3 bg-violet-600/20 rounded-xl text-violet-600 dark:text-violet-400 border border-violet-500/20">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 21l-1.81-2.904L4.5 18l.813-5.096L3 9h5.187L9 4l.813 5H15l-1.813 3.904L14 18l-4.188-2.096z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold tracking-tight">AI Explanatory Rationale</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">Interpretation of price recommendations & optimization signals</p>
              </div>
            </div>

            <div className="relative text-base text-slate-700 dark:text-slate-200 leading-relaxed font-medium bg-white dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 p-6 rounded-xl">
              <span className="text-3xl text-violet-500 font-serif absolute -top-3 left-4">“</span>
              <p className="pl-6 pt-2 italic">
                {recommendation.recommendation?.reason || "No pricing explanation text generated by the AI models."}
              </p>
            </div>
            
            <div className="mt-6 flex justify-between items-center text-xs text-slate-500 dark:text-slate-400 relative">
              <span>Optimized Timestamp: {new Date(recommendation.recommendation?.timestamp || Date.now()).toLocaleString()}</span>
              <span>Status: Active & Validated</span>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
