import { useState } from 'react';
import { aiAPI, downloadBlob } from '../api/client';
import { useToast } from '../context/ToastContext';
import {
  FileText, FileDown, FileSpreadsheet, Download, Printer, Loader2,
  TrendingUp, TrendingDown, Minus, ArrowUpRight, ArrowDownRight,
  BrainCircuit, Sparkles, Target, BarChart3, ShieldCheck, Info,
} from 'lucide-react';

const fmtMoney = (v, currency = '$') =>
  v == null ? '—' : `${currency}${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

const fmtNum = (v, digits = 1) =>
  v == null ? '—' : Number(v).toLocaleString(undefined, { maximumFractionDigits: digits });

function Trend({ value, suffix = '%', goodWhenPositive = true }) {
  if (value == null) return <span className="text-surface-400">—</span>;
  const up = value > 0;
  const positive = goodWhenPositive ? up : !up;
  const Icon = value === 0 ? Minus : up ? TrendingUp : TrendingDown;
  return (
    <span className={`inline-flex items-center gap-1 text-sm font-bold ${positive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
      <Icon className="w-4 h-4" />
      {value > 0 ? '+' : ''}{value.toFixed(1)}{suffix}
    </span>
  );
}

function SectionHead({ n, title, icon: Icon }) {
  return (
    <div className="flex items-center gap-2.5 mb-3">
      <span className="flex items-center justify-center w-6 h-6 rounded-lg bg-primary-600 text-white text-xs font-bold shrink-0">{n}</span>
      <Icon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
      <h3 className="text-[11px] font-bold uppercase tracking-wider text-surface-700 dark:text-surface-300">{title}</h3>
    </div>
  );
}

// Tiny inline sparkline for the historical price series (renders only when
// the backend actually provides ≥2 price points — never fabricated).
function PriceSparkline({ points }) {
  if (!points || points.length < 2) return null;
  const prices = points.map((p) => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const w = 120, h = 28;
  const step = w / (prices.length - 1);
  const coords = prices.map((p, i) => {
    const x = i * step;
    const y = h - 3 - ((p - min) / range) * (h - 6);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const up = prices[prices.length - 1] >= prices[0];
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="block">
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke={up ? '#10b981' : '#ef4444'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Stat({ label, value, sub, accent, mono }) {
  return (
    <div className={`p-3 rounded-xl border ${
      accent
        ? 'border-primary-200 dark:border-primary-800 bg-primary-50/60 dark:bg-primary-900/20'
        : 'border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-700/30'
    }`}>
      <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">{label}</p>
      <div className={`mt-1 text-lg font-bold text-surface-900 dark:text-white ${mono ? 'font-mono' : ''}`}>{value}</div>
      {sub &&      <p className="text-[10px] text-surface-400 mt-0.5 truncate" title={typeof sub === 'string' ? sub : undefined}>{sub}</p>}
    </div>
  );
}

export default function AiAnalysisReport({ product, report, loading }) {
  const toast = useToast();
  const [exporting, setExporting] = useState(null);

  if (!report && !loading) return null;

  const handleExport = async (format) => {
    setExporting(format);
    try {
      const res = await aiAPI.exportReport(product.id, format);
      downloadBlob(res, `ai_analysis_report_${product.id}.${format === 'xlsx' ? 'xlsx' : format}`);
      toast.success('Report exported', `${format.toUpperCase()} downloaded`);
    } catch (err) {
      toast.error('Export failed', err.response?.data?.detail);
    } finally {
      setExporting(null);
    }
  };

  const handlePrint = () => window.print();

  const d = report?.prediction_details;
  const mp = report?.model_performance;
  const ri = report?.revenue_impact;
  const factors = report?.why_factors?.slice(0, 3) || [];
  const pt = report?.price_trend || {};

  return (
    <div className="report-print-area" id="ai-analysis-report">
      <div className="card overflow-hidden print:shadow-none">
        {/* Compact header */}
        <div className="bg-gradient-to-r from-primary-700 via-primary-600 to-primary-500 px-5 py-4 text-white flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-white/15">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold leading-tight">AI Analysis Report</h2>
              <p className="text-[11px] text-white/80">
                {product?.name || ''}{report?.category ? ` · ${report.category}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap print:hidden">
            {[
              { f: 'pdf', label: 'PDF', icon: FileDown },
              { f: 'xlsx', label: 'Excel', icon: FileSpreadsheet },
              { f: 'csv', label: 'CSV', icon: Download },
            ].map(({ f, label, icon: Icon }) => (
              <button
                key={f}
                onClick={() => handleExport(f)}
                disabled={exporting !== null}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/15 hover:bg-white/25 text-[11px] font-semibold transition-colors disabled:opacity-50"
              >
                {exporting === f ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                {label}
              </button>
            ))}
            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white text-primary-700 text-[11px] font-semibold hover:bg-primary-50 transition-colors"
            >
              <Printer className="w-3.5 h-3.5" /> Print
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-5 space-y-4">
            {[0, 1, 2].map((i) => <div key={i} className="skeleton h-16 w-full rounded-xl" />)}
            <p className="text-center text-sm text-surface-500 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary-500" /> Generating analysis report…
            </p>
          </div>
        ) : !report?.available ? (
          <div className="p-5">
            <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
              <Info className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">Report unavailable</p>
                <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">{report?.message}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-5 space-y-6">
            {/* 1. Prediction summary */}
            <section>
              <SectionHead n={1} title="Prediction Summary" icon={Target} />
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Stat label="Current Price" value={fmtMoney(d?.current_price, report.currency)} mono />
                <Stat
                  label="Recommended Price"
                  value={fmtMoney(d?.recommended_price, report.currency)}
                  sub={d.recommended_price >= d.current_price
                    ? <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400"><ArrowUpRight className="w-3 h-3" />vs current</span>
                    : <span className="inline-flex items-center gap-0.5 text-red-600 dark:text-red-400"><ArrowDownRight className="w-3 h-3" />vs current</span>}
                  accent
                  mono
                />
                <Stat label="Price Change" value={<Trend value={d?.percentage_change} />} sub={`${fmtMoney(d?.difference, report.currency)} absolute`} />
                <Stat label="Confidence" value={d?.confidence_score != null ? `${fmtNum(d.confidence_score)}%` : '—'} sub={d?.best_model || 'best model'} />
              </div>
              {/* Price Trend — from recorded price history / catalog anchors */}
              {pt.trend && (
                <div className="mt-3 flex items-center justify-between gap-4 p-3 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-700/30">
                  <div className="flex items-center gap-3">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">Price Trend</p>
                    {pt.trend === 'increasing' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-xs font-bold">
                        <TrendingUp className="w-3.5 h-3.5" /> Increasing {pt.change_pct != null && pt.change_pct > 0 ? `+${pt.change_pct.toFixed(1)}%` : ''}
                      </span>
                    )}
                    {pt.trend === 'decreasing' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
                        <TrendingDown className="w-3.5 h-3.5" /> Decreasing {pt.change_pct != null ? `${pt.change_pct.toFixed(1)}%` : ''}
                      </span>
                    )}
                    {pt.trend === 'stable' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-300 text-xs font-bold">
                        <Minus className="w-3.5 h-3.5" /> Stable {pt.change_pct != null && pt.change_pct !== 0 ? `${pt.change_pct > 0 ? '+' : ''}${pt.change_pct.toFixed(1)}%` : ''}
                      </span>
                    )}
                    <span className="text-[10px] text-surface-400 hidden sm:inline">
                      {pt.source === 'pricing_history' ? 'from recorded price history' : pt.source === 'catalog_base_price' ? 'catalog base vs current price' : 'price history'}
                    </span>
                  </div>
                  <PriceSparkline points={pt.points} />
                </div>
              )}
              {/* Future Price Forecast — projected from dated price history */}
              {report?.price_forecast?.available && (
                <div className="mt-3 p-3 rounded-xl border border-primary-200 dark:border-primary-800 bg-primary-50/40 dark:bg-primary-900/10">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-surface-400">
                      Future Price Forecast
                    </p>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 text-[10px] font-semibold">
                      {report.price_forecast.trend === 'increasing' && <><TrendingUp className="w-3 h-3" /> Increasing</>}
                      {report.price_forecast.trend === 'decreasing' && <><TrendingDown className="w-3 h-3" /> Decreasing</>}
                      {report.price_forecast.trend === 'stable' && <><Minus className="w-3 h-3" /> Stable</>}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                    {(report.price_forecast.horizons || []).slice(0, 5).map((h) => (
                      <div key={h.days} className="p-2 rounded-lg bg-white/60 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 text-center">
                        <p className="text-[10px] font-medium text-surface-400">{h.days}D</p>
                        {h.reliable === false ? (
                          <p className="text-sm font-bold text-surface-400">—</p>
                        ) : (
                          <p className="text-sm font-bold font-mono text-surface-900 dark:text-white">{fmtMoney(h.price, report.currency)}</p>
                        )}
                        <p className="text-[9px] text-surface-400 font-mono">
                          {h.reliable === false ? 'beyond range' : `${fmtMoney(h.lower, report.currency)}–${fmtMoney(h.upper, report.currency)}`}
                        </p>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 text-[10px] text-surface-500 dark:text-surface-400">
                    {report.price_forecast.note}{report.price_forecast.confidence != null && ` Confidence ${fmtNum(report.price_forecast.confidence, 0)}%.`}
                  </p>
                </div>
              )}
            </section>

            {/* 2. Why this price — top 3 factors */}
            <section>
              <SectionHead n={2} title="Why This Price?" icon={BrainCircuit} />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {factors.map((f) => (
                  <div key={f.factor} className="p-3.5 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-700/30">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-surface-900 dark:text-white truncate" title={f.factor}>{f.factor}</p>
                      <span className="px-2 py-0.5 rounded-md bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 text-[10px] font-semibold shrink-0">{f.impact}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                        <div className="h-1.5 bg-primary-500 rounded-full" style={{ width: `${Math.min(f.importance, 100)}%` }} />
                      </div>
                      <span className="text-[10px] font-medium text-surface-400 whitespace-nowrap">{f.importance}%</span>
                    </div>
                    <p className="mt-2 text-[11px] leading-relaxed text-surface-600 dark:text-surface-400">{f.explanation}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* 3. Model performance */}
            <section>
              <SectionHead n={3} title="Model Performance" icon={BarChart3} />
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                <Stat label="Best Model" value={mp?.best_model || '—'} sub={`R² ${mp?.r2 != null ? mp.r2.toFixed(3) : '—'}`} />
                <Stat label="R² Score" value={mp?.r2 != null ? mp.r2.toFixed(3) : '—'} sub="coefficient of determination" mono />
                <Stat label="MAE" value={fmtMoney(mp?.mae, report.currency)} sub="mean absolute error" mono />
                <Stat label="RMSE" value={fmtMoney(mp?.rmse, report.currency)} sub="root mean squared error" mono />
                <Stat
                  label="Training Data"
                  value={fmtNum(mp?.dataset_records, 0)}
                  sub={d?.training_dataset_name || `${mp?.num_features ?? 0} features`}
                />
              </div>
            </section>

            {/* 4. Business impact */}
            <section>
              <SectionHead n={4} title="Business Impact" icon={Sparkles} />
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Stat label="Expected Revenue (30d)" value={fmtMoney(ri?.predicted_revenue, report.currency)} accent mono />
                <Stat label="Expected Profit (30d)" value={fmtMoney(d?.expected_profit, report.currency)} mono />
                <Stat label="Revenue vs Current" value={<Trend value={ri?.revenue_increase_pct} />} sub={`${fmtMoney(ri?.revenue_increase, report.currency)} absolute`} />
                <Stat label="Profit vs Current" value={<Trend value={ri?.profit_increase_pct} />} sub={`${fmtMoney(ri?.profit_increase, report.currency)} absolute`} />
              </div>
            </section>

            {/* 5. Final recommendation */}
            <section>
              <SectionHead n={5} title="Final AI Recommendation" icon={ShieldCheck} />
              <div className="p-4 rounded-xl border-l-4 border-l-primary-500 bg-primary-50/40 dark:bg-primary-900/10 border-y border-r border-primary-100 dark:border-primary-800/50">
                <p className="text-sm leading-relaxed text-surface-700 dark:text-surface-300">{report.conclusion}</p>
              </div>
            </section>

            {/* Footer meta */}
            <div className="flex items-center justify-between text-[10px] text-surface-400 border-t border-surface-200 dark:border-surface-700 pt-3">
              <span>Generated by PricePilot AI from the trained model, uploaded dataset & sales history</span>
              <span>{report.generated_at ? new Date(report.generated_at).toLocaleString() : ''}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
