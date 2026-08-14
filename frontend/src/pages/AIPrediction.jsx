import { useState, useEffect, useCallback } from 'react';
import { aiAPI, productsAPI, pricingAPI, downloadBlob } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import ConfirmDialog from '../components/ConfirmDialog';
import ForecastingPanel from '../components/ForecastingPanel';
import AiAnalysisReport from '../components/AiAnalysisReport';
import {
  BrainCircuit, Loader2, Sparkles, CheckCircle2, AlertCircle,
  RefreshCw, TrendingUp, TrendingDown, ArrowRight, Search,
  Layers, Database, XCircle, Gauge, LineChart as LineChartIcon, Minus,
  Cpu, FileSpreadsheet, CalendarClock, ListChecks, Timer, FileText,
} from 'lucide-react';

export default function AIPrediction() {
  const { user } = useAuth();
  const toast = useToast();
  const [status, setStatus] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [training, setTraining] = useState(false);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [analyzing, setAnalyzing] = useState(null); // product id being analyzed
  const [results, setResults] = useState({}); // productId -> analysis
  const [batchLoading, setBatchLoading] = useState(false);
  const [saveTarget, setSaveTarget] = useState(null);
  const [saving, setSaving] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  // AI Prediction Analysis Report: auto-generates after a prediction completes.
  const [reportProduct, setReportProduct] = useState(null); // product the report is for
  const [report, setReport] = useState(null);               // report payload
  const [reportLoading, setReportLoading] = useState(false);
  // Deep-link support: /ai?tab=forecasting opens the Demand Forecasting tab
  // (used by the dashboard's "Generate Forecast" quick action).
  const [tab, setTab] = useState(
    () => new URLSearchParams(window.location.search).get('tab') === 'forecasting' ? 'forecasting' : 'optimization'
  );

  const isAdminOrPricing = user?.role === 'admin' || user?.role === 'pricing_manager';

  const fetchStatus = useCallback(async () => {
    try {
      const res = await aiAPI.getStatus();
      setStatus(res.data);
      setTraining(!!res.data?.training_in_progress);
    } catch { /* ignore */ }
  }, []);

  const fetchModelInfo = useCallback(async () => {
    try {
      const res = await aiAPI.modelInfo();
      setModelInfo(res.data);
    } catch { /* ignore */ }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await productsAPI.getCategories();
      setCategories(res.data);
    } catch { /* ignore */ }
  }, []);

  const fetchRecommendations = useCallback(async () => {
    try {
      const res = await pricingAPI.listRecommendations({ limit: 10 });
      setRecommendations(res.data);
    } catch { /* ignore */ }
  }, []);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 50 };
      if (search) params.search = search;
      if (category) params.category = category;
      const res = await productsAPI.list(params);
      setProducts(res.data.items);
    } catch (err) {
      toast.error('Failed to load products', err.response?.data?.detail);
    } finally {
      setLoading(false);
    }
  }, [search, category, toast]);

  useEffect(() => {
    fetchStatus();
    fetchModelInfo();
    fetchCategories();
    fetchRecommendations();
  }, [fetchStatus, fetchModelInfo, fetchCategories, fetchRecommendations]);

  // Poll while training is running so the Model Info card updates when done.
  useEffect(() => {
    if (!training) return undefined;
    const id = setInterval(() => {
      fetchStatus();
      fetchModelInfo();
    }, 4000);
    return () => clearInterval(id);
  }, [training, fetchStatus, fetchModelInfo]);

  useEffect(() => {
    const timer = setTimeout(() => fetchProducts(), 300);
    return () => clearTimeout(timer);
  }, [search, category, fetchProducts]);

  const runAnalysis = async (product, options = {}) => {
    setAnalyzing(product.id);
    try {
      // Predict always uses the persisted model - never retrains per request.
      const res = await aiAPI.predict(product.id, options.includeForecast ? { include_forecast: true } : {});
      setResults((prev) => ({ ...prev, [product.id]: res.data }));
      // Auto-generate the AI Analysis Report after every completed prediction.
      loadReport(product);
    } catch (err) {
      toast.error('Analysis failed', err.response?.data?.detail);
    } finally {
      setAnalyzing(null);
    }
  };

  const loadReport = async (product, options = {}) => {
    setReportProduct(product);
    setReportLoading(true);
    setReport(null);
    try {
      const res = await aiAPI.report(product.id, options.horizon);
      setReport(res.data);
    } catch (err) {
      toast.error('Report generation failed', err.response?.data?.detail);
    } finally {
      setReportLoading(false);
    }
  };

  const handleRetrain = async () => {
    setTraining(true);
    try {
      const res = await aiAPI.retrain();
      toast.success('Training started', res.data.message);
    } catch (err) {
      setTraining(false);
      toast.error('Training could not start', err.response?.data?.detail);
    }
  };

  // Handoff from the Demand Forecasting tab: run optimization with the Prophet
  // demand signal folded into the suggested price.
  const handleUseInOptimization = (product, forecast) => {
    setTab('optimization');
    setSearch('');
    setCategory('');
    setResults((prev) => ({
      ...prev,
      [product.id]: { ...(prev[product.id] || {}), demand_forecast: forecast?.metrics || {} },
    }));
    runAnalysis(product, { includeForecast: true });
    const m = forecast?.metrics || {};
    const trendText = m.trend === 'up' ? 'rising demand' : m.trend === 'down' ? 'softening demand' : 'stable demand';
    toast.success(
      'Demand forecast applied',
      `Optimizing "${product.name}" with ${trendText} (${m.source === 'prophet' ? 'Prophet' : 'trend'} signal)`
    );
  };

  const runBatch = async () => {
    setBatchLoading(true);
    try {
      const res = await aiAPI.batchOptimize({ category: category || undefined });
      const map = {};
      res.data.results.forEach((r) => { map[r.product_id] = r; });
      setResults(map);
      toast.success('Batch analysis complete', `${res.data.total_analyzed} products analyzed`);
    } catch (err) {
      toast.error('Batch analysis failed', err.response?.data?.detail);
    } finally {
      setBatchLoading(false);
    }
  };

  const saveRecommendation = async () => {
    if (!saveTarget) return;
    setSaving(true);
    try {
      const res = await aiAPI.saveRecommendation(saveTarget.id);
      toast.success('Recommendation saved', res.data.message);
      setResults((prev) => ({ ...prev, [saveTarget.id]: { ...prev[saveTarget.id], saved: true } }));
      fetchRecommendations();
    } catch (err) {
      toast.error('Could not save', err.response?.data?.detail);
    } finally {
      setSaving(false);
      setSaveTarget(null);
    }
  };

  const handleApprove = async (rec) => {
    try {
      const res = await pricingAPI.approveRecommendation(rec.id);
      toast.success('Applied', res.data.message);
      fetchRecommendations();
      fetchStatus();
    } catch (err) {
      toast.error('Failed to apply', err.response?.data?.detail);
    }
  };

  const handleReject = async (rec) => {
    try {
      const res = await pricingAPI.rejectRecommendation(rec.id);
      toast.info('Rejected', res.data.message);
      fetchRecommendations();
    } catch (err) {
      toast.error('Failed to reject', err.response?.data?.detail);
    }
  };

  const ready = status?.status === 'ready';

  return (
    <div className="page-transition space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">AI Price Prediction</h1>
          <p className="text-surface-500 dark:text-surface-400 mt-1">
            Random Forest, XGBoost & Linear Regression trained on your pricing data
          </p>
        </div>
        <button onClick={() => { fetchStatus(); fetchRecommendations(); }} className="btn-secondary btn-sm">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1.5 rounded-xl bg-surface-100 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 w-fit max-w-full overflow-x-auto">
        <button
          onClick={() => setTab('optimization')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
            tab === 'optimization'
              ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-300 shadow-sm'
              : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-200'
          }`}
        >
          <Gauge className="w-4 h-4" />
          Price Optimization
        </button>
        <button
          onClick={() => setTab('forecasting')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
            tab === 'forecasting'
              ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-300 shadow-sm'
              : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-200'
          }`}
        >
          <LineChartIcon className="w-4 h-4" />
          Demand Forecasting
        </button>
      </div>

      {tab === 'forecasting' ? (
        <ForecastingPanel onUseInOptimization={handleUseInOptimization} />
      ) : (
      <>
      {/* Model Status Panel */}
      <div className={`card overflow-hidden border-l-4 ${ready ? 'border-l-emerald-500' : 'border-l-amber-500'}`}>
        <div className="card-body">
          <div className="flex flex-col lg:flex-row lg:items-center gap-6">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${ready ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-amber-100 dark:bg-amber-900/30'}`}>
                <BrainCircuit className={`w-7 h-7 ${ready ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`} />
              </div>
              <div>
                <p className="text-sm font-semibold text-surface-900 dark:text-white">
                  {ready ? 'AI Engine Ready' : 'Insufficient Data'}
                </p>
                <p className="text-xs text-surface-500 dark:text-surface-400">
                  {ready
                    ? `Trained on ${status.samples} records · Best model: ${status.best_model}`
                    : `Need ${status?.min_samples_required ?? 10}+ records; currently ${status?.samples ?? 0}. Upload a dataset to train.`}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-6 lg:ml-auto">
              <div className="text-center">
                <p className="text-xl font-bold text-surface-900 dark:text-white">{status?.samples ?? 0}</p>
                <p className="text-xs text-surface-500">Training Samples</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-amber-600 dark:text-amber-400">{status?.recommendations_pending ?? 0}</p>
                <p className="text-xs text-surface-500">Pending Review</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{status?.recommendations_applied ?? 0}</p>
                <p className="text-xs text-surface-500">Applied</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-red-600 dark:text-red-400">{status?.recommendations_rejected ?? 0}</p>
                <p className="text-xs text-surface-500">Rejected</p>
              </div>
            </div>
          </div>

          {!ready && (
            <div className="mt-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-amber-700 dark:text-amber-300">
                Upload a pricing dataset in <span className="font-semibold">Dataset Management</span> or add more products
                to enable real model training. The engine uses Random Forest, XGBoost, and Linear Regression with
                cross-validation to select the best model.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Model Information Card */}
      <div className="card overflow-hidden border-l-4 border-l-primary-500">
        <div className="card-header flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
              <Cpu className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white">AI Model Information</h3>
              <p className="text-xs text-surface-500">Trained on your uploaded dataset — prediction uses the persisted model</p>
            </div>
          </div>
          {isAdminOrPricing && (
            <button onClick={handleRetrain} disabled={training} className="btn-primary btn-sm">
              {training ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {training ? 'Training…' : 'Retrain Model'}
            </button>
          )}
        </div>
        <div className="card-body">
          {training && (
            <div className="mb-4 flex items-center gap-3 p-3 rounded-xl bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
              <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
              <p className="text-sm text-primary-700 dark:text-primary-300">
                AI models are training in the background on your latest catalog and sales history — this page refreshes automatically.
              </p>
            </div>
          )}
          {!modelInfo || !modelInfo.has_model ? (
            <div className="p-4 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-surface-900 dark:text-white">No trained model yet</p>
                <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
                  {modelInfo?.message || 'Upload a dataset, import it into the catalog, and AI training runs automatically — or click Retrain Model.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { label: 'Best Model', value: modelInfo.best_model || '—', sub: `R² ${modelInfo.accuracy ?? '—'}` },
                { label: 'Accuracy (R²)', value: modelInfo.accuracy != null ? `${(modelInfo.accuracy * 100).toFixed(1)}%` : '—', sub: `MAE $${(modelInfo.mae ?? 0).toFixed(2)} · RMSE $${(modelInfo.rmse ?? 0).toFixed(2)}` },
                { label: 'Training Dataset', value: modelInfo.dataset_name || 'Catalog', sub: `#${modelInfo.dataset_id || '—'}` },
                { label: 'Training Records', value: modelInfo.samples ?? 0, sub: `${(modelInfo.features_used?.length ?? 0)} features` },
                { label: 'Training Date', value: modelInfo.created_at ? new Date(modelInfo.created_at).toLocaleDateString() : '—', sub: modelInfo.created_at ? new Date(modelInfo.created_at).toLocaleTimeString() : '—' },
              ].map((item) => (
                <div key={item.label} className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">{item.label}</p>
                  <p className="text-base font-bold text-surface-900 dark:text-white mt-1 truncate" title={item.value}>{item.value}</p>
                  <p className="text-[10px] text-surface-400 mt-0.5 truncate">{item.sub}</p>
                </div>
              ))}
            </div>
          )}

          {modelInfo?.has_model && (
            <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                <p className="flex items-center gap-1.5 text-[11px] font-medium text-surface-500 mb-2">
                  <ListChecks className="w-3.5 h-3.5" /> Features Used ({modelInfo.features_used?.length ?? 0})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(modelInfo.features_used || []).slice(0, 18).map((f) => (
                    <span key={f} className="px-2 py-0.5 rounded-md bg-surface-100 dark:bg-surface-700 text-[10px] font-mono text-surface-600 dark:text-surface-300">{f}</span>
                  ))}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-surface-500 flex items-center gap-1.5">
                    <CalendarClock className="w-3.5 h-3.5" /> Last Retrained
                  </span>
                  <span className="font-medium text-surface-900 dark:text-white">
                    {modelInfo.created_at ? new Date(modelInfo.created_at).toLocaleString() : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-surface-500 flex items-center gap-1.5">
                    <Timer className="w-3.5 h-3.5" /> Training Time
                  </span>
                  <span className="font-medium text-surface-900 dark:text-white">
                    {modelInfo.training_time_seconds != null ? `${modelInfo.training_time_seconds.toFixed(1)}s` : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-surface-500 flex items-center gap-1.5">
                    <FileSpreadsheet className="w-3.5 h-3.5" /> Status
                  </span>
                  <span className={`badge ${modelInfo.status === 'ready' ? 'badge-success' : modelInfo.status === 'training' ? 'badge-info' : 'badge-danger'}`}>
                    {modelInfo.status}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filters + Batch */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[220px] relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
              <input
                type="text"
                className="input pl-9"
                placeholder="Search products..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              className="input w-auto min-w-[160px]"
              value={category}
              onChange={(e) => { setCategory(e.target.value); }}
            >
              <option value="">All Categories</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            {isAdminOrPricing && (
              <button onClick={runBatch} disabled={batchLoading || !ready} className="btn-primary">
                {batchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                Analyze All
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Pending Recommendations */}
      {recommendations.filter((r) => r.status === 'pending').length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-sm font-semibold text-surface-900 dark:text-white">Pending Recommendations</h3>
          </div>
          <div className="card-body space-y-3">
            {recommendations.filter((r) => r.status === 'pending').map((rec) => (
              <div key={rec.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-surface-50 dark:bg-surface-700/40 border border-surface-200 dark:border-surface-700">
                <div>
                  <p className="text-sm font-medium text-surface-900 dark:text-white">{rec.product_name}</p>
                  <p className="text-xs text-surface-500 mt-0.5">
                    ${rec.current_price.toFixed(2)} <ArrowRight className="w-3 h-3 inline" /> ${rec.recommended_price.toFixed(2)} · Confidence {rec.confidence_score?.toFixed(0)}%
                  </p>
                </div>
                {isAdminOrPricing && (
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleApprove(rec)} className="btn-success btn-sm">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                    </button>
                    <button onClick={() => handleReject(rec)} className="btn-ghost btn-sm text-red-500">
                      <XCircle className="w-3.5 h-3.5" /> Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analysis Results Grid */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-50 dark:bg-surface-800/50">
                <th className="table-header">Product</th>
                <th className="table-header">Current</th>
                <th className="table-header">AI Suggested</th>
                <th className="table-header">Change</th>
                <th className="table-header">Confidence</th>
                <th className="table-header">Best Model</th>
                <th className="table-header text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-16">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-primary-500" />
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-16">
                    <Database className="w-12 h-12 text-surface-300 dark:text-surface-600 mx-auto mb-3" />
                    <p className="text-sm text-surface-500 dark:text-surface-400">No products found</p>
                  </td>
                </tr>
              ) : (
                products.map((product) => {
                  const analysis = results[product.id];
                  const isAnalyzing = analyzing === product.id;
                  const changePct = analysis?.expected_revenue_change;
                  return (
                    <tr key={product.id} className="table-row">
                      <td className="table-cell">
                        <p className="font-medium text-surface-900 dark:text-white">{product.name}</p>
                        <p className="text-xs text-surface-400">{product.sku}</p>
                      </td>
                      <td className="table-cell font-mono">${product.current_price?.toFixed(2)}</td>
                      <td className="table-cell">
                        {analysis?.suggested_price ? (
                          <span className="font-mono font-semibold text-primary-600 dark:text-primary-400">
                            ${analysis.suggested_price.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-surface-400 text-xs">{analysis?.insufficient_data ? 'Needs data' : '—'}</span>
                        )}
                      </td>
                      <td className="table-cell">
                        {changePct !== null && changePct !== undefined ? (
                          <span className={`inline-flex items-center gap-1 text-xs font-medium ${changePct >= 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                            {changePct >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                            {changePct >= 0 ? '+' : ''}{changePct.toFixed(1)}%
                          </span>
                        ) : <span className="text-surface-400">—</span>}
                      </td>
                      <td className="table-cell">
                        {analysis?.confidence_score ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-surface-200 dark:bg-surface-700 rounded-full h-1.5">
                              <div className="bg-primary-500 h-1.5 rounded-full" style={{ width: `${analysis.confidence_score}%` }}></div>
                            </div>
                            <span className="text-xs font-medium">{analysis.confidence_score.toFixed(0)}%</span>
                          </div>
                        ) : <span className="text-surface-400">—</span>}
                      </td>
                      <td className="table-cell">
                        {analysis?.best_model ? (
                          <span className="badge-info">{analysis.best_model}</span>
                        ) : <span className="text-surface-400">—</span>}
                        {analysis?.demand_forecast?.trend && analysis.demand_forecast.trend !== 'unavailable' && (
                          <span className={`ml-1.5 inline-flex items-center gap-1 badge ${
                            analysis.demand_forecast.trend === 'up'
                              ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                              : analysis.demand_forecast.trend === 'down'
                                ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                                : 'bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-300'
                          }`} title="Demand forecast signal">
                            {analysis.demand_forecast.trend === 'up' ? <TrendingUp className="w-3 h-3" />
                              : analysis.demand_forecast.trend === 'down' ? <TrendingDown className="w-3 h-3" />
                              : <Minus className="w-3 h-3" />}
                            {analysis.demand_forecast.growth_pct != null
                              ? `${analysis.demand_forecast.growth_pct > 0 ? '+' : ''}${analysis.demand_forecast.growth_pct}%`
                              : analysis.demand_forecast.trend}
                          </span>
                        )}
                      </td>
                      <td className="table-cell text-right">
                        {isAdminOrPricing ? (
                          analysis?.suggested_price ? (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => loadReport(product)}
                                className="btn-outline btn-sm"
                                title="Generate AI Analysis Report"
                              >
                                <FileText className="w-3.5 h-3.5" /> Report
                              </button>
                              {analysis.saved ? (
                                <span className="badge-success">Sent to approval</span>
                              ) : (
                                <button onClick={() => setSaveTarget(product)} className="btn-primary btn-sm">
                                  <Sparkles className="w-3.5 h-3.5" /> Save
                                </button>
                              )}
                            </div>
                          ) : (
                            <button onClick={() => runAnalysis(product)} disabled={isAnalyzing} className="btn-secondary btn-sm">
                              {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BrainCircuit className="w-4 h-4" />}
                              Analyze
                            </button>
                          )
                        ) : analysis?.suggested_price ? (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => loadReport(product)}
                              className="btn-outline btn-sm"
                              title="Generate AI Analysis Report"
                            >
                              <FileText className="w-3.5 h-3.5" /> Report
                            </button>
                            <span className="badge-info">View only</span>
                          </div>
                        ) : (
                          <span className="text-xs text-surface-400">Admin only</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Save confirm */}
      <ConfirmDialog
        open={saveTarget !== null}
        title="Save AI recommendation?"
        message={saveTarget
          ? `Send the AI suggestion for "${saveTarget.name}" to the pricing approval queue?`
          : ''}
        confirmLabel="Save"
        danger={false}
        loading={saving}
        onConfirm={saveRecommendation}
        onCancel={() => setSaveTarget(null)}
      />

      {/* AI Prediction Analysis Report */}
      {(reportProduct || reportLoading) && (
        <AiAnalysisReport
          product={reportProduct}
          report={report}
          loading={reportLoading}
        />
      )}
      </>
      )}
    </div>
  );
}
