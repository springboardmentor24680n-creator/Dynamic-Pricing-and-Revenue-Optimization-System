import { useState, useEffect, useRef } from 'react';
import { productsAPI } from '../api/client';
import { useToast } from '../context/ToastContext';
import {
  Search, Loader2, AlertCircle, Package, X, CheckCircle2,
} from 'lucide-react';

function formatPrice(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

/**
 * Searchable product selector.
 *
 * Searches the REAL catalog dynamically (name, brand, category, SKU) with a
 * debounced call to the products API — never hardcoded. Selecting a product
 * reports the full product object (including its ID) to the parent, so the
 * selected product remains the single source of truth for the page.
 */
export default function ProductSearchSelect({
  value,
  onSelect,
  placeholder = 'Search products by name, brand, category or SKU…',
  disabled = false,
  autoSelectFirst = false,
}) {
  const toast = useToast();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const seq = useRef(0);
  const boxRef = useRef(null);

  // Hydrate the selected product from its ID (e.g. when a product was chosen
  // in the Forecasting tab and the user navigated here).
  useEffect(() => {
    if (value && value !== selected?.id) {
      productsAPI
        .getById(value)
        .then((res) => setSelected(res.data))
        .catch(() => setSelected(null));
    } else if (!value) {
      setSelected(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Debounced dynamic search against the real catalog.
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      setError(null);
      setLoading(false);
      setOpen(false);
      return;
    }
    setLoading(true);
    setError(null);
    const id = ++seq.current;
    const timer = setTimeout(async () => {
      try {
        const res = await productsAPI.list({ search: q, limit: 20, sort_by: 'name', sort_order: 'asc' });
        if (id !== seq.current) return;
        const items = res.data.items || [];
        setResults(items);
        setOpen(true);
        if (autoSelectFirst && items.length === 1) {
          pick(items[0]);
        }
      } catch (err) {
        if (id !== seq.current) return;
        setResults([]);
        setError(err.response?.data?.detail || 'Search failed. Please try again.');
        setOpen(true);
      } finally {
        if (id === seq.current) setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  // Close the dropdown when clicking outside the component.
  useEffect(() => {
    const onDocClick = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const pick = (p) => {
    setSelected(p);
    setQuery('');
    setResults([]);
    setError(null);
    setOpen(false);
    onSelect?.(p);
  };

  const clear = () => {
    setSelected(null);
    setQuery('');
    setResults([]);
    setOpen(false);
    onSelect?.(null);
  };

  return (
    <div className="relative" ref={boxRef}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400 pointer-events-none" />
        <input
          type="text"
          className="input pl-9 pr-9"
          placeholder={placeholder}
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (query.trim() || results.length || error) setOpen(true); }}
        />
        {selected && !query && (
          <button
            onClick={clear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-red-500 transition-colors"
            title="Clear selection"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Selected product chip */}
      {selected && !query && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="badge-info inline-flex items-center gap-1.5 max-w-full">
            <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{selected.name}</span>
          </span>
          <span className="badge-neutral text-[10px]">#{selected.id}</span>
          <span className="badge-neutral text-[10px] font-mono">{selected.sku}</span>
          <span className="badge-neutral text-[10px]">{selected.category}</span>
          <span className="badge-neutral text-[10px] font-mono">{formatPrice(selected.current_price)}</span>
        </div>
      )}

      {/* Search results dropdown */}
      {open && (
        <div className="absolute z-30 mt-1 w-full rounded-xl border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-800 shadow-xl max-h-72 overflow-y-auto">
          {loading && (
            <div className="flex items-center gap-2 px-4 py-3 text-sm text-surface-500 dark:text-surface-400">
              <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
              Searching catalog…
            </div>
          )}
          {!loading && error && (
            <div className="flex items-start gap-2 px-4 py-3 text-sm text-red-600 dark:text-red-400">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {error}
            </div>
          )}
          {!loading && !error && results.length === 0 && query.trim() && (
            <div className="px-4 py-6 text-center">
              <Package className="w-8 h-8 text-surface-300 dark:text-surface-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-surface-700 dark:text-surface-200">No products found</p>
              <p className="text-xs text-surface-400 mt-0.5">
                Try another name, brand, category or SKU.
              </p>
            </div>
          )}
          {!loading && !error && results.map((p) => (
            <button
              key={p.id}
              onClick={() => pick(p)}
              className="w-full text-left px-4 py-2.5 hover:bg-surface-50 dark:hover:bg-surface-700/60 transition-colors border-b border-surface-100 dark:border-surface-700/60 last:border-0 flex items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-surface-900 dark:text-white truncate">{p.name}</p>
                <p className="text-xs text-surface-400 truncate">
                  {p.category} · {p.sku} · #{p.id}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-sm font-mono font-semibold text-primary-600 dark:text-primary-400">
                  {formatPrice(p.current_price)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}