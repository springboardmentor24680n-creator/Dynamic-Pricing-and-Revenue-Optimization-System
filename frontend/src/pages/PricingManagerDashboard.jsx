import React, { useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function PricingManagerDashboard({
  products,
  pricingForm,
  setPricingForm,
  recommendation,
  history,
  alerts,
  formatCurrency,
  handlePricingSubmit,
  isSubmittingPricing,
  clearHistory,
  showToast,
  loadData
}) {
  const [isApplying, setIsApplying] = useState(false);

  const selectedProduct = products.find(
    (item) => String(item.id) === String(pricingForm.product)
  );

  const handleApplyPrice = async () => {
    if (!selectedProduct || !recommendation) return;
    
    const suggestedPrice = recommendation.suggestedPrice || recommendation.recommendation?.recommended_price;
    if (!suggestedPrice) return;

    setIsApplying(true);
    try {
      const payload = {
        name: selectedProduct.name,
        category: selectedProduct.category || "Online Retail",
        current_price: Number(suggestedPrice),
        cost_price: selectedProduct.cost_price || Number((selectedProduct.current_price * 0.7).toFixed(2)),
        stock: selectedProduct.stock || 150
      };
      
      const token = localStorage.getItem("token");
      await axios.put(`${API}/products/${selectedProduct.id}`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      showToast(`Applied price of ${formatCurrency(suggestedPrice)} to ${selectedProduct.name} successfully!`, "success");
      if (loadData) {
        await loadData();
      }
    } catch (err) {
      console.error("Failed to apply price:", err);
      showToast("Failed to apply price. Ensure you are logged in with appropriate credentials.", "error");
    } finally {
      setIsApplying(false);
    }
  };

  const getRecommendationBadge = (rec) => {
    const action = String(rec).toLowerCase();
    if (action.includes("increase")) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/30">
          Increase Price
        </span>
      );
    }
    if (action.includes("decrease")) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/30">
          Decrease Price
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
        Maintain Price
      </span>
    );
  };

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6 space-y-6">
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Selector & Details Card */}
        <div className="lg:col-span-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Price Optimization</h2>
          </div>
          
          <form onSubmit={handlePricingSubmit} className="space-y-4">
            <div>
              <label htmlFor="productSelect" className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Target Product (SKU)</label>
              <select
                id="productSelect"
                value={pricingForm.product}
                onChange={(e) => {
                  const selectedId = e.target.value;
                  const prod = products.find((item) => String(item.id) === String(selectedId));
                  setPricingForm({
                    ...pricingForm,
                    product: selectedId,
                    basePrice: prod ? prod.current_price : pricingForm.basePrice,
                  });
                }}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500 font-medium text-sm"
                required
              >
                {products.length > 0 ? (
                  products.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} (SKU: {item.id})
                    </option>
                  ))
                ) : (
                  <option value="">Select a product</option>
                )}
              </select>
            </div>

            {selectedProduct && (
              <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Current Price:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">{formatCurrency(selectedProduct.current_price)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Inventory Level:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">{selectedProduct.stock} units</span>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmittingPricing}
              className="w-full py-2.5 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:text-slate-400 text-white rounded-xl font-semibold text-sm transition cursor-pointer"
            >
              {isSubmittingPricing ? "Optimizing..." : "Get Recommendation"}
            </button>
          </form>


        </div>

        {/* Signals & Session Logs (Right Column) */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
          <div>
            <div className="border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Active Signal Alerts</h2>
            </div>
            <ul className="space-y-2">
              {alerts.length > 0 ? (
                alerts.slice(0, 3).map((alert) => (
                  <li
                    key={alert.id}
                    className={`flex gap-3 p-3.5 border rounded-xl text-xs font-medium text-left ${
                      alert.type === "warning"
                        ? "bg-rose-50/50 border-rose-200 text-rose-700 dark:bg-rose-950/20 dark:border-rose-900/30 dark:text-rose-400"
                        : alert.type === "success"
                        ? "bg-emerald-50/50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/20 dark:border-emerald-900/30 dark:text-emerald-400"
                        : "bg-blue-50/50 border-blue-200 text-blue-700 dark:bg-blue-950/20 dark:border-blue-900/30 dark:text-blue-400"
                    }`}
                  >
                    <span className="mt-0.5">
                      {alert.type === "warning" ? "⚠️" : alert.type === "success" ? "✅" : "ℹ️"}
                    </span>
                    <span>{alert.message}</span>
                  </li>
                ))
              ) : (
                <li className="text-center py-6 text-slate-500 dark:text-slate-400 text-xs">No active pricing signals registered.</li>
              )}
            </ul>
          </div>

          {history.length > 0 && (
            <div>
              <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">Session logs</h2>
                <button
                  type="button"
                  onClick={clearHistory}
                  className="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer font-semibold"
                >
                  Clear Logs
                </button>
              </div>
              <ul className="space-y-2.5 max-h-48 overflow-y-auto pr-1">
                {history.map((item) => (
                  <li key={item.id} className="flex justify-between items-center text-xs border-b border-slate-50 dark:border-slate-850 pb-2">
                    <span className="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-xs">{item.product}</span>
                    <span className="text-slate-500 font-mono text-xs">{formatCurrency(item.basePrice)} → {formatCurrency(item.suggestedPrice)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
