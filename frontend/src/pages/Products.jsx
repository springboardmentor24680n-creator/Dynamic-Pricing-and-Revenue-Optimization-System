import { useState, useEffect, useCallback } from 'react';
import { productsAPI, datasetsAPI, downloadBlob } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import ConfirmDialog from '../components/ConfirmDialog';
import {
  Package, Plus, Search, Edit2, Trash2, ChevronLeft, ChevronRight,
  Loader2, X, AlertCircle, RefreshCw, ImageOff, Tag, TrendingUp,
  Download, Upload, CheckSquare, Square, ArrowUpDown, Power,
} from 'lucide-react';

const PLACEHOLDER_IMG = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">
    <rect fill="#e2e8f0" width="80" height="80"/>
    <text x="40" y="42" text-anchor="middle" dominant-baseline="central" fill="#94a3b8" font-family="system-ui" font-size="10">No Image</text>
  </svg>`
);

export default function Products() {
  const { user } = useAuth();
  const toast = useToast();
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(20);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selected, setSelected] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    name: '', sku: '', category: '', base_price: 0, current_price: 0,
    cost_price: 0, stock_quantity: 0, image_url: '', description: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [bulkConfirm, setBulkConfirm] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);

  const isAdminOrPricing = user?.role === 'admin' || user?.role === 'pricing_manager';
  const isAdmin = user?.role === 'admin';

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = { skip: page * limit, limit, sort_by: sortBy, sort_order: sortOrder };
      if (debouncedSearch) params.search = debouncedSearch;
      if (category) params.category = category;
      if (statusFilter) params.status = statusFilter;
      const res = await productsAPI.list(params);
      setProducts(res.data.items);
      setTotal(res.data.total);
      setSelected([]);
    } catch (err) {
      toast.error('Failed to load products', err.response?.data?.detail);
    } finally {
      setLoading(false);
    }
  }, [page, category, limit, debouncedSearch, sortBy, sortOrder, statusFilter, toast]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await productsAPI.getCategories();
      setCategories(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, [fetchProducts, fetchCategories]);

  // Debounce the search input so each keystroke doesn't fire an API call
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const toggleSort = (col) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortOrder('desc');
    }
  };

  const openCreate = () => {
    setEditingProduct(null);
    setFormData({
      name: '', sku: '', category: '', base_price: 0, current_price: 0,
      cost_price: 0, stock_quantity: 0, image_url: '', description: '',
    });
    setError('');
    setModalOpen(true);
  };

  const openEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      sku: product.sku,
      category: product.category || '',
      base_price: product.base_price,
      current_price: product.current_price,
      cost_price: product.cost_price || 0,
      stock_quantity: product.stock_quantity || 0,
      image_url: product.image_url || '',
      description: product.description || '',
    });
    setError('');
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      if (editingProduct) {
        await productsAPI.update(editingProduct.id, formData);
        toast.success('Product updated', `${formData.name} was saved successfully`);
      } else {
        await productsAPI.create(formData);
        toast.success('Product created', `${formData.name} added to the catalog`);
      }
      setModalOpen(false);
      fetchProducts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save product');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    const id = deleteConfirm;
    setDeleteConfirm(null);
    try {
      await productsAPI.delete(id);
      toast.success('Product deleted', 'The product was removed from the catalog');
      fetchProducts();
    } catch (err) {
      toast.error('Delete failed', err.response?.data?.detail);
    }
  };

  const handleBulkDelete = async () => {
    if (!bulkConfirm) return;
    setBulkConfirm(null);
    try {
      const res = await productsAPI.bulkDelete(selected);
      toast.success('Products deleted', res.data.message);
      fetchProducts();
    } catch (err) {
      toast.error('Bulk delete failed', err.response?.data?.detail);
    }
  };

  const handleToggleStatus = async (product) => {
    const newStatus = product.status === 'active' ? 'inactive' : 'active';
    try {
      await productsAPI.toggleStatus(product.id, newStatus);
      toast.success('Status updated', `${product.name} is now ${newStatus}`);
      fetchProducts();
    } catch (err) {
      toast.error('Failed to update status', err.response?.data?.detail);
    }
  };

  const handleBulkStatus = async (status) => {
    try {
      const res = await productsAPI.bulkStatus(selected, status);
      toast.success('Bulk update', res.data.message);
      fetchProducts();
    } catch (err) {
      toast.error('Bulk update failed', err.response?.data?.detail);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await productsAPI.exportCsv({ category: category || undefined, search: search || undefined });
      downloadBlob(res, 'products.csv');
      toast.success('Export complete', 'Products exported as CSV');
    } catch (err) {
      toast.error('Export failed', 'Could not generate CSV');
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImporting(true);
    try {
      const res = await datasetsAPI.upload(file, 'retail-pricing');
      toast.success('File processed', res.data.message || 'Dataset processed');
      fetchProducts();
    } catch (err) {
      toast.error('Import failed', err.response?.data?.detail || 'Could not process file');
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  };

  const toggleSelect = (id) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const toggleSelectAll = () => {
    if (selected.length === products.length) setSelected([]);
    else setSelected(products.map((p) => p.id));
  };

  const totalPages = Math.ceil(total / limit);
  const SortableHeader = ({ col, children, className = '' }) => (
    <th
      className={`table-header cursor-pointer select-none hover:text-surface-900 dark:hover:text-white transition-colors ${className}`}
      onClick={() => toggleSort(col)}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        <ArrowUpDown className={`w-3 h-3 ${sortBy === col ? 'text-primary-500' : 'text-surface-300 dark:text-surface-600'}`} />
      </span>
    </th>
  );

  return (
    <div className="page-transition space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Product Management</h1>
          <p className="text-surface-500 dark:text-surface-400 mt-1">
            <span className="font-medium text-surface-700 dark:text-surface-300">{total}</span> products in your catalog
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={handleExport} disabled={exporting || products.length === 0} className="btn-secondary btn-sm">
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Export CSV
          </button>
          {isAdminOrPricing && (
            <>
              <label className="btn-outline btn-sm cursor-pointer">
                {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                Import CSV
                <input type="file" accept=".csv,.xlsx" className="hidden" onChange={handleImport} />
              </label>
              <button onClick={openCreate} className="btn-primary btn-sm">
                <Plus className="w-4 h-4" />
                Add Product
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[220px] relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
              <input
                type="text"
                className="input pl-9"
                placeholder="Search by name, brand, category or SKU... (e.g. laptop, Samsung, iPhone)"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              />
            </div>
            <select
              className="input w-auto min-w-[160px]"
              value={category}
              onChange={(e) => { setCategory(e.target.value); setPage(0); }}
            >
              <option value="">All Categories</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              className="input w-auto min-w-[130px]"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <select
              className="input w-auto min-w-[120px]"
              value={limit}
              onChange={(e) => { setLimit(Number(e.target.value)); setPage(0); }}
            >
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
            <button onClick={() => { setPage(0); fetchProducts(); }} className="btn-primary">
              Apply
            </button>
            {(search || category || statusFilter) && (
              <button onClick={() => { setSearch(''); setCategory(''); setStatusFilter(''); setPage(0); }} className="btn-ghost">
                <X className="w-4 h-4" /> Clear
              </button>
            )}
          </div>

          {/* Bulk actions */}
          {selected.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-3 p-3 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 animate-fade-in">
              <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                {selected.length} selected
              </span>
              {isAdminOrPricing && (
                <>
                  <button onClick={() => handleBulkStatus('active')} className="btn-secondary btn-sm">
                    <Power className="w-3.5 h-3.5" /> Activate
                  </button>
                  <button onClick={() => handleBulkStatus('inactive')} className="btn-secondary btn-sm">
                    <Power className="w-3.5 h-3.5" /> Deactivate
                  </button>
                  {isAdmin && (
                    <button onClick={() => setBulkConfirm(true)} className="btn-danger btn-sm">
                      <Trash2 className="w-3.5 h-3.5" /> Delete Selected
                    </button>
                  )}
                </>
              )}
              <button onClick={() => setSelected([])} className="btn-ghost btn-sm ml-auto">
                <X className="w-3.5 h-3.5" /> Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Loading / Empty / Table */}
      {loading ? (
        <div className="card overflow-hidden">
          <div className="divide-y divide-surface-200 dark:divide-surface-700">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-6 py-4">
                <div className="skeleton w-10 h-10 rounded-lg"></div>
                <div className="skeleton h-4 w-48"></div>
                <div className="skeleton h-4 w-20 ml-auto"></div>
              </div>
            ))}
          </div>
        </div>
      ) : products.length === 0 ? (
        <div className="card">
          <div className="card-body text-center py-16">
            <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
              <Package className="w-10 h-10 text-surface-400" />
            </div>
            <h3 className="text-lg font-semibold text-surface-900 dark:text-white mb-1">No products found</h3>
            <p className="text-sm text-surface-500 dark:text-surface-400 max-w-sm mx-auto">
              {search || category || statusFilter
                ? 'Try adjusting your search or filter criteria.'
                : 'Get started by adding your first product or importing a CSV.'}
            </p>
            {isAdminOrPricing && !search && !category && !statusFilter && (
              <button onClick={openCreate} className="btn-primary btn-sm mt-6">
                <Plus className="w-4 h-4" /> Add your first product
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-50 dark:bg-surface-800/50">
                  <th className="table-header w-10">
                    <button onClick={toggleSelectAll} className="text-surface-500 hover:text-primary-600 transition-colors">
                      {selected.length === products.length
                        ? <CheckSquare className="w-4 h-4 text-primary-500" />
                        : <Square className="w-4 h-4" />}
                    </button>
                  </th>
                  <SortableHeader col="name">Product</SortableHeader>
                  <th className="table-header">SKU</th>
                  <th className="table-header">Category</th>
                  <SortableHeader col="price">Price</SortableHeader>
                  <th className="table-header">Cost</th>
                  <th className="table-header">Margin</th>
                  <SortableHeader col="stock">Stock</SortableHeader>
                  <SortableHeader col="revenue">Revenue</SortableHeader>
                  <th className="table-header">Status</th>
                  {isAdminOrPricing && <th className="table-header text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
                {products.map((product) => {
                  const margin = product.cost_price
                    ? ((product.current_price - product.cost_price) / product.current_price * 100).toFixed(1)
                    : null;
                  return (
                    <tr key={product.id} className="table-row">
                      <td className="table-cell">
                        <button onClick={() => toggleSelect(product.id)} className="text-surface-500 hover:text-primary-600 transition-colors">
                          {selected.includes(product.id)
                            ? <CheckSquare className="w-4 h-4 text-primary-500" />
                            : <Square className="w-4 h-4" />}
                        </button>
                      </td>
                      <td className="table-cell">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-surface-100 dark:bg-surface-800 overflow-hidden flex-shrink-0">
                            <img
                              src={product.image_url || PLACEHOLDER_IMG}
                              alt={product.name}
                              className="w-full h-full object-cover"
                              onError={(e) => { e.target.src = PLACEHOLDER_IMG; }}
                              loading="lazy"
                            />
                          </div>
                          <span className="font-medium text-surface-900 dark:text-white truncate max-w-[220px]">{product.name}</span>
                        </div>
                      </td>
                      <td className="table-cell text-surface-500 font-mono text-xs">{product.sku}</td>
                      <td className="table-cell">
                        <span className="badge-neutral flex items-center gap-1 w-fit">
                          <Tag className="w-3 h-3" /> {product.category || 'Uncategorized'}
                        </span>
                      </td>
                      <td className="table-cell font-mono font-semibold text-surface-900 dark:text-white">${product.current_price?.toFixed(2)}</td>
                      <td className="table-cell font-mono text-surface-500">${product.cost_price?.toFixed(2) ?? '—'}</td>
                      <td className="table-cell">
                        {margin !== null ? (
                          <span className={`badge ${margin >= 40 ? 'badge-success' : margin >= 20 ? 'badge-warning' : 'badge-danger'}`}>
                            {margin}%
                          </span>
                        ) : <span className="text-surface-400">—</span>}
                      </td>
                      <td className="table-cell">
                        <span className={`badge ${
                          product.stock_quantity > 10 ? 'badge-success'
                          : product.stock_quantity > 0 ? 'badge-warning'
                          : 'badge-danger'
                        }`}>
                          {product.stock_quantity || 0}
                        </span>
                      </td>
                      <td className="table-cell font-mono text-xs">${(product.revenue || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                      <td className="table-cell">
                        <button
                          onClick={() => handleToggleStatus(product)}
                          className={`badge cursor-pointer transition-all hover:opacity-80 ${
                            product.status === 'active' ? 'badge-success' : 'badge-neutral'
                          }`}
                          title={isAdminOrPricing ? 'Click to toggle status' : product.status}
                        >
                          <Power className="w-3 h-3 mr-1" />
                          {product.status}
                        </button>
                      </td>
                      {isAdminOrPricing && (
                        <td className="table-cell text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button onClick={() => openEdit(product)} className="btn-ghost btn-sm p-1.5" title="Edit product">
                              <Edit2 className="w-4 h-4" />
                            </button>
                            {isAdmin && (
                              <button
                                onClick={() => setDeleteConfirm(product.id)}
                                className="btn-ghost btn-sm p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                                title="Delete product"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="card">
          <div className="flex items-center justify-between px-6 py-4">
            <p className="text-sm text-surface-500">
              Showing {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
            </p>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0} className="btn-secondary btn-sm disabled:opacity-40">
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const start = Math.max(0, Math.min(page - 2, totalPages - 5));
                const pageNum = start + i;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`btn-sm min-w-[36px] ${pageNum === page ? 'btn-primary' : 'btn-secondary'}`}
                  >
                    {pageNum + 1}
                  </button>
                );
              })}
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="btn-secondary btn-sm disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal-content max-w-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="card-header flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                {editingProduct ? 'Edit Product' : 'Add Product'}
              </h2>
              <button onClick={() => setModalOpen(false)} className="btn-ghost p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              {error && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="label">Product Name</label>
                  <input className="input" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required placeholder="e.g. Wireless Bluetooth Headphones" />
                </div>
                <div>
                  <label className="label">SKU</label>
                  <input className="input" value={formData.sku} onChange={(e) => setFormData({ ...formData, sku: e.target.value })} required placeholder="e.g. ELEC-001" />
                </div>
                <div>
                  <label className="label">Category</label>
                  <input className="input" value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} placeholder="e.g. Electronics" list="category-suggestions" />
                  <datalist id="category-suggestions">
                    {categories.map((c) => <option key={c} value={c} />)}
                  </datalist>
                </div>
                <div>
                  <label className="label">Base Price ($)</label>
                  <input type="number" step="0.01" min="0" className="input" value={formData.base_price} onChange={(e) => setFormData({ ...formData, base_price: parseFloat(e.target.value) || 0 })} required />
                </div>
                <div>
                  <label className="label">Current Price ($)</label>
                  <input type="number" step="0.01" min="0" className="input" value={formData.current_price} onChange={(e) => setFormData({ ...formData, current_price: parseFloat(e.target.value) || 0 })} required />
                </div>
                <div>
                  <label className="label">Cost Price ($)</label>
                  <input type="number" step="0.01" min="0" className="input" value={formData.cost_price} onChange={(e) => setFormData({ ...formData, cost_price: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <label className="label">Stock Quantity</label>
                  <input type="number" min="0" className="input" value={formData.stock_quantity} onChange={(e) => setFormData({ ...formData, stock_quantity: parseInt(e.target.value) || 0 })} />
                </div>
                <div className="col-span-2">
                  <label className="label">Image URL</label>
                  <input className="input" value={formData.image_url} onChange={(e) => setFormData({ ...formData, image_url: e.target.value })} placeholder="https://example.com/image.jpg" />
                </div>
                <div className="col-span-2">
                  <label className="label">Description</label>
                  <textarea className="input" rows="3" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="Describe your product..." />
                </div>
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
                <button onClick={handleSave} disabled={saving || !formData.name || !formData.sku} className="btn-primary">
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingProduct ? 'Save Changes' : 'Create Product'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteConfirm !== null}
        title="Delete product?"
        message="This will permanently remove the product and its pricing history. This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleteConfirm(null)}
      />

      {/* Bulk delete confirm */}
      <ConfirmDialog
        open={bulkConfirm !== null}
        title={`Delete ${selected.length} products?`}
        message="All selected products will be permanently removed from the catalog."
        confirmLabel="Delete Selected"
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkConfirm(null)}
      />
    </div>
  );
}
