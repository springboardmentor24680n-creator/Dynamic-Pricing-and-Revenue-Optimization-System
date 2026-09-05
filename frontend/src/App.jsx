import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";
import AIDashboard from "./pages/AIDashboard";
import ForecastVisualization from "./pages/ForecastVisualization";
import AIRecommendation from "./pages/AIRecommendation";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";
import AIMonitoring from "./pages/AIMonitoring";
import PredictionHistory from "./pages/PredictionHistory";
import PricingManagerDashboard from "./pages/PricingManagerDashboard";
import BusinessAnalystDashboard from "./pages/BusinessAnalystDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import SeasonalTrendReports from "./pages/SeasonalTrendReports";
import CompetitorMonitoring from "./pages/CompetitorMonitoring";
import PricingComparisonReports from "./pages/PricingComparisonReports";
import MarketIntelligence from "./pages/MarketIntelligence";
import ProfitabilityAnalytics from "./pages/ProfitabilityAnalytics";
import PricingStrategyRecommendations from "./pages/PricingStrategyRecommendations";
import ExecutiveBIReports from "./pages/ExecutiveBIReports";


const API = "http://127.0.0.1:8000";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const roleOptions = [
  { value: "pricing manager", label: "Pricing Manager" },
  { value: "business analyst", label: "Business Analyst" },
  { value: "admin", label: "Admin" },
];

function formatINR(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value || 0);
}
const formatCurrency = formatINR;

export default function App() {
  const [token, setToken] = useState(() => {
    const savedToken = localStorage.getItem("token") || "";
    if (savedToken) {
      try {
        const payload = JSON.parse(atob(savedToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
        if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
          localStorage.removeItem("token");
          localStorage.removeItem("userName");
          localStorage.removeItem("userRole");
          return "";
        }
      } catch (e) {
        localStorage.removeItem("token");
        localStorage.removeItem("userName");
        localStorage.removeItem("userRole");
        return "";
      }
    }
    return savedToken;
  });
  const [mode, setMode] = useState("login");
  const [userName, setUserName] = useState("");
  const [userRole, setUserRole] = useState(
    localStorage.getItem("userRole") || "pricing manager",
  );
  const [error, setError] = useState("");

  const [productsError, setProductsError] = useState(false);
  const [dashboardError, setDashboardError] = useState(false);
  const [overviewError, setOverviewError] = useState(false);
  const [salesError, setSalesError] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const [auth, setAuth] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    role: "pricing manager",
  });

  const [pricingForm, setPricingForm] = useState({
    product: "",
    basePrice: 0,
    competitorPrice: 132,
    demandLevel: 78,
    inventoryLevel: 42,
  });

  const [products, setProducts] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [overviewMetrics, setOverviewMetrics] = useState(null);
  const [salesInfo, setSalesInfo] = useState({ count: 0, sample: [] });
  const [googleReady, setGoogleReady] = useState(false);

  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");

  const toggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    localStorage.setItem("theme", nextTheme);
    if (nextTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") || "light";
    if (savedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, []);
  const [history, setHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [recommendation, setRecommendation] = useState(null);
  const [productForm, setProductForm] = useState({
    id: null,
    name: "",
    category: "",
    current_price: "",
    cost_price: "",
    stock: "",
  });
  const [productMessage, setProductMessage] = useState({ type: "", text: "" });
  const [isSavingProduct, setIsSavingProduct] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeAnchor, setActiveAnchor] = useState("");

  // Submit and Toast states
  const [isSubmittingAuth, setIsSubmittingAuth] = useState(false);
  const [isSubmittingPricing, setIsSubmittingPricing] = useState(false);
  const [toast, setToast] = useState({ show: false, message: "", type: "success" });

  const showToast = (message, type = "success") => {
    setToast({ show: true, message, type });
  };

  useEffect(() => {
    if (!toast.show) return;
    const timer = setTimeout(() => {
      setToast(prev => ({ ...prev, show: false }));
    }, 4000);
    return () => clearTimeout(timer);
  }, [toast.show]);

  // Product Catalog table states
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogSortField, setCatalogSortField] = useState("name");
  const [catalogSortOrder, setCatalogSortOrder] = useState("asc");
  const [catalogPage, setCatalogPage] = useState(1);

  // Pricing table states
  const [pricingSearch, setPricingSearch] = useState("");
  const [pricingSortField, setPricingSortField] = useState("name");
  const [pricingSortOrder, setPricingSortOrder] = useState("asc");
  const [pricingPage, setPricingPage] = useState(1);

  // Sales table states
  const [salesSearch, setSalesSearch] = useState("");
  const [salesSortField, setSalesSortField] = useState("product_name");
  const [salesSortOrder, setSalesSortOrder] = useState("asc");
  const [salesPage, setSalesPage] = useState(1);

  const getFilteredCatalog = () => {
    let result = [...products];
    if (catalogSearch.trim()) {
      const q = catalogSearch.toLowerCase();
      result = result.filter(item => 
        (item.name || "").toLowerCase().includes(q) ||
        (item.category || "").toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      let aVal = a[catalogSortField];
      let bVal = b[catalogSortField];
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      if (aVal < bVal) return catalogSortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return catalogSortOrder === "asc" ? 1 : -1;
      return 0;
    });
    return result;
  };
  const catalogItemsPerPage = 5;
  const filteredCatalog = getFilteredCatalog();
  const totalCatalogPages = Math.ceil(filteredCatalog.length / catalogItemsPerPage) || 1;
  const paginatedCatalog = filteredCatalog.slice(
    (catalogPage - 1) * catalogItemsPerPage,
    catalogPage * catalogItemsPerPage
  );

  const getFilteredPricing = () => {
    let result = [...products];
    if (pricingSearch.trim()) {
      const q = pricingSearch.toLowerCase();
      result = result.filter(item => 
        (item.name || "").toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      let aVal = a[pricingSortField];
      let bVal = b[pricingSortField];
      if (pricingSortField === "suggested") {
        aVal = a.id === pricingForm.product && recommendation ? recommendation.suggestedPrice : a.current_price;
        bVal = b.id === pricingForm.product && recommendation ? recommendation.suggestedPrice : b.current_price;
      }
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      if (aVal < bVal) return pricingSortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return pricingSortOrder === "asc" ? 1 : -1;
      return 0;
    });
    return result;
  };
  const pricingItemsPerPage = 5;
  const filteredPricing = getFilteredPricing();
  const totalPricingPages = Math.ceil(filteredPricing.length / pricingItemsPerPage) || 1;
  const paginatedPricing = filteredPricing.slice(
    (pricingPage - 1) * pricingItemsPerPage,
    pricingPage * pricingItemsPerPage
  );

  const getFilteredSales = () => {
    let result = [...(salesInfo.sample || [])];
    if (salesSearch.trim()) {
      const q = salesSearch.toLowerCase();
      result = result.filter(item => 
        (item.product_name || "").toLowerCase().includes(q)
      );
    }
    result.sort((a, b) => {
      let aVal = a[salesSortField];
      let bVal = b[salesSortField];
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      if (aVal < bVal) return salesSortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return salesSortOrder === "asc" ? 1 : -1;
      return 0;
    });
    return result;
  };
  const salesItemsPerPage = 5;
  const filteredSales = getFilteredSales();
  const totalSalesPages = Math.ceil(filteredSales.length / salesItemsPerPage) || 1;
  const paginatedSales = filteredSales.slice(
    (salesPage - 1) * salesItemsPerPage,
    salesPage * salesItemsPerPage
  );

  function renderNavIcon(label) {
    const l = label.toLowerCase();
    if (l.includes("executive") || l.includes("bi")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      );
    }
    if (l.includes("dashboard")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      );
    }
    if (l.includes("product")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3"/>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
          <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>
        </svg>
      );
    }
    if (l.includes("analytics")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>
          <path d="M22 12A10 10 0 0 0 12 2v10z"/>
        </svg>
      );
    }
    if (l.includes("monitoring")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      );
    }
    if (l.includes("logs")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="8" y1="6" x2="21" y2="6"/>
          <line x1="8" y1="12" x2="21" y2="12"/>
          <line x1="8" y1="18" x2="21" y2="18"/>
          <line x1="3" y1="6" x2="3.01" y2="6"/>
          <line x1="3" y1="12" x2="3.01" y2="12"/>
          <line x1="3" y1="18" x2="3.01" y2="18"/>
        </svg>
      );
    }
    if (l.includes("strategy") || l.includes("optimizer") || l.includes("forecast") || l.includes("insights") || l.includes("outlook") || l.includes("planner") || l.includes("projections") || l.includes("recommend")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="20" x2="18" y2="10"/>
          <line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
      );
    }
    if (l.includes("history") || l.includes("actions")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      );
    }
    if (l.includes("alert") || l.includes("quality") || l.includes("verification") || l.includes("pulse")) {
      return (
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
      );
    }
    return (
      <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="16"/>
        <line x1="8" y1="12" x2="16" y2="12"/>
      </svg>
    );
  }

  function renderMetricCard(metric) {
    const label = metric.label.toLowerCase();
    let icon = null;
    let trend = null;
    let progress = 75;

    if (label.includes("revenue") || label.includes("pulse")) {
      icon = (
        <svg className="metric-icon blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/>
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
      );
      trend = <span className="metric-trend positive">+14.2% vs last month</span>;
      progress = 84;
    } else if (label.includes("units") || label.includes("sold")) {
      icon = (
        <svg className="metric-icon green" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
      );
      trend = <span className="metric-trend positive">+8.6% week-over-week</span>;
      progress = 68;
    } else if (label.includes("average") || label.includes("price") || label.includes("suggested") || label.includes("ai")) {
      icon = (
        <svg className="metric-icon purple" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 14 14"/>
        </svg>
      );
      trend = <span className="metric-trend neutral">Model Optimized</span>;
      progress = 92;
    } else if (label.includes("confidence")) {
      icon = (
        <svg className="metric-icon orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
      );
      trend = <span className="metric-trend positive">High Reliability</span>;
      progress = 95;
    } else if (label.includes("alerts")) {
      icon = (
        <svg className="metric-icon red" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      );
      trend = metric.value > 0 ? <span className="metric-trend negative">Attention Required</span> : <span className="metric-trend positive">All Clear</span>;
      progress = metric.value > 0 ? 30 : 100;
    } else {
      icon = (
        <svg className="metric-icon blue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="16"/>
          <line x1="8" y1="12" x2="16" y2="12"/>
        </svg>
      );
      trend = <span className="metric-trend neutral">Active Monitoring</span>;
      progress = 75;
    }

    return (
      <article key={metric.label} className="dashboard-card metric-card-enhanced">
        <div className="metric-card-header">
          <div className="metric-icon-wrap">{icon}</div>
          <span className="metric-card-label">{metric.label}</span>
        </div>
        <div className="metric-card-body">
          <strong className="metric-card-value">{metric.value}</strong>
          {trend}
        </div>
        <div className="metric-progress-wrapper">
          <div className="metric-progress-bar">
            <div className="metric-progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
        </div>
        <p className="metric-card-desc">{metric.description}</p>
      </article>
    );
  }

  function renderSalesTable() {
    return (
      <div className="verification-box">
        <p>
          Loaded sales rows:
          <strong> {salesInfo.count || "0"}</strong>
        </p>
        <div className="table-search-bar">
          <input
            type="text"
            placeholder="Search sales..."
            value={salesSearch}
            onChange={(e) => {
              setSalesSearch(e.target.value);
              setSalesPage(1);
            }}
            className="table-search-input"
          />
        </div>
        <div className="table-wrap">
          <table className="sample-table">
            <thead>
              <tr>
                <th onClick={() => {
                  setSalesSortOrder(salesSortField === "product_name" && salesSortOrder === "asc" ? "desc" : "asc");
                  setSalesSortField("product_name");
                }} style={{ cursor: "pointer" }}>
                  Product {salesSortField === "product_name" ? (salesSortOrder === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => {
                  setSalesSortOrder(salesSortField === "price" && salesSortOrder === "asc" ? "desc" : "asc");
                  setSalesSortField("price");
                }} style={{ cursor: "pointer" }}>
                  Price {salesSortField === "price" ? (salesSortOrder === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => {
                  setSalesSortOrder(salesSortField === "quantity_sold" && salesSortOrder === "asc" ? "desc" : "asc");
                  setSalesSortField("quantity_sold");
                }} style={{ cursor: "pointer" }}>
                  Qty Sold {salesSortField === "quantity_sold" ? (salesSortOrder === "asc" ? "▲" : "▼") : ""}
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedSales.length > 0 ? (
                paginatedSales.map((row, index) => (
                  <tr key={index}>
                    <td>{row.product_name}</td>
                    <td>{formatCurrency(row.price)}</td>
                    <td>{row.quantity_sold || row.units_sold}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="3" style={{ textAlign: "center", padding: "20px" }}>
                    No sales sample loaded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="table-pagination">
          <button
            type="button"
            disabled={salesPage === 1}
            onClick={() => setSalesPage(prev => Math.max(prev - 1, 1))}
            className="pagination-btn"
          >
            Prev
          </button>
          <span className="pagination-info">Page {salesPage} of {totalSalesPages}</span>
          <button
            type="button"
            disabled={salesPage === totalSalesPages}
            onClick={() => setSalesPage(prev => Math.min(prev + 1, totalSalesPages))}
            className="pagination-btn"
          >
            Next
          </button>
        </div>
      </div>
    );
  }

  const headers = {
    Authorization: `Bearer ${token}`,
  };

  function getNormalizedRole(role) {
    const normalized = (role || "pricing manager").toLowerCase().trim();

    if (normalized.includes("manager")) return "pricing manager";
    if (normalized.includes("analyst")) return "business analyst";
    if (normalized.includes("admin")) return "admin";
    if (normalized.includes("user")) return "business analyst";

    return "pricing manager";
  }

  function getRoleDisplayName(role) {
    switch (getNormalizedRole(role)) {
      case "business analyst":
        return "Business Analyst";
      case "admin":
        return "Admin";
      default:
        return "Pricing Manager";
    }
  }

  function getRoleCopy(role) {
    switch (getNormalizedRole(role)) {
      case "business analyst":
        return {
          title: "Business Analysis Workspace",
          subtitle:
            "Review sales performance, demand signals, and forecast scenarios.",
          highlight: "Analyst focus",
        };
      case "admin":
        return {
          title: "Admin Control Center",
          subtitle: "Manage database connection telemetry, system audit events, and ML models versioning.",
          highlight: "Admin focus",
        };
      default:
        return {
          title: "Pricing Manager Console",
          subtitle:
            "Lead price decisions, monitor demand, and protect margin health.",
          highlight: "Manager focus",
        };
    }
  }

  async function register() {
    setIsSubmittingAuth(true);
    try {
      await axios.post(`${API}/auth/register`, {
        ...auth,
        role: getNormalizedRole(auth.role),
      });
      showToast("Registration successful! Please login.", "success");
      setMode("login");
    } catch (error) {
      console.error("Registration failed", error);
      const detail = error.response?.data?.detail || "Registration failed. Try again.";
      showToast(detail, "error");
    } finally {
      setIsSubmittingAuth(false);
    }
  }

  async function login() {
    setIsSubmittingAuth(true);
    try {
      const response = await axios.post(`${API}/auth/login`, {
        email: auth.email,
        password: auth.password,
      });

      const normalizedRole = getNormalizedRole(response.data.role || auth.role);

      localStorage.setItem("token", response.data.access_token);
      localStorage.setItem("userName", auth.email.split("@")[0]);
      localStorage.setItem("userRole", normalizedRole);
      setUserName(auth.email.split("@")[0]);
      setUserRole(normalizedRole);
      setToken(response.data.access_token);
      setActiveView("dashboard");
      setActiveAnchor("");
      showToast("Logged in successfully!", "success");
    } catch (error) {
      console.error("Login failed", error);
      const detail = error.response?.data?.detail || "Login failed. Check your credentials.";
      showToast(detail, "error");
    } finally {
      setIsSubmittingAuth(false);
    }
  }

  function decodeGoogleCredential(credential) {
    try {
      const payload = credential.split(".")[1];
      const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
      const padLength = (4 - (normalized.length % 4)) % 4;
      const padded = normalized + "=".repeat(padLength);
      const decoded = atob(padded);
      const jsonPayload = decodeURIComponent(
        decoded
          .split("")
          .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
          .join(""),
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      return null;
    }
  }

  // Handle credential response callback from Google
  async function handleGoogleCredentialResponse(response) {
    const role = getNormalizedRole(auth.role);
    const profile = decodeGoogleCredential(response.credential);

    try {
      const googleResponse = await axios.post(`${API}/auth/google`, {
        credential: response.credential,
        email: profile?.email || "",
        name: profile?.name || profile?.given_name || "",
        role,
      });

      const userName =
        profile?.name ||
        profile?.given_name ||
        googleResponse.data.user_name ||
        "Google User";
      const normalizedRole = getNormalizedRole(
        googleResponse.data.role || role,
      );

      localStorage.setItem("token", googleResponse.data.access_token);
      localStorage.setItem("userName", userName);
      localStorage.setItem("userRole", normalizedRole);
      setUserName(userName);
      setUserRole(normalizedRole);
      setToken(googleResponse.data.access_token);
      showToast("Logged in with Google successfully!", "success");
    } catch (error) {
      console.error("Google sign-in failed", error);
      showToast("Google sign-in failed. Please try again.", "error");
    }
  }

  async function loadData() {
    setIsLoadingData(true);
    setError("");
    setProductsError(false);
    setDashboardError(false);
    setOverviewError(false);
    setSalesError(false);

    try {
      // 1. Fetch Products
      try {
        const productsResponse = await axios.get(`${API}/products`, { headers });
        const fetchedProducts = productsResponse.data;
        setProducts(fetchedProducts);
        if (fetchedProducts.length > 0) {
          const firstProduct = fetchedProducts[0];
          setPricingForm((prev) => ({
            ...prev,
            product: firstProduct.id,
            basePrice: firstProduct.current_price,
          }));
        }
        generateAlerts(fetchedProducts);
      } catch (err) {
        console.error("Error loading products:", err);
        setProductsError(true);
      }

      // 2. Fetch Dashboard stats
      try {
        const dashboardResponse = await axios.get(`${API}/dashboard`, { headers });
        setDashboard(dashboardResponse.data);
      } catch (err) {
        console.error("Error loading dashboard:", err);
        setDashboardError(true);
      }

      // 3. Fetch Overview metrics
      try {
        const overviewResponse = await axios.get(`${API}/api/dashboard/overview`, { headers });
        setOverviewMetrics(overviewResponse.data.overview);
      } catch (err) {
        console.error("Error loading overview metrics:", err);
        setOverviewError(true);
      }

      // 4. Fetch Sales count & sample
      try {
        const salesCountResponse = await axios.get(`${API}/sales/count`);
        const salesCount = salesCountResponse.data.sales_count;
        const salesSampleResponse = await axios.get(`${API}/sales`);
        setSalesInfo({
          count: salesCount,
          sample: salesSampleResponse.data,
        });
      } catch (err) {
        console.error("Error loading sales data:", err);
        setSalesError(true);
      }

      const savedHistory = JSON.parse(
        localStorage.getItem("pricingHistory") || "[]"
      );
      setHistory(savedHistory);
    } finally {
      setIsLoadingData(false);
    }
  }

  function generateAlerts(fetchedProducts) {
    const activeProducts = fetchedProducts || products;
    const dynamicAlerts = [];
    let alertId = 1;

    // 1. Stock warning alerts
    const lowStockProducts = activeProducts.filter(p => p.stock < 15);
    lowStockProducts.slice(0, 2).forEach(p => {
      dynamicAlerts.push({
        id: alertId++,
        type: "warning",
        message: `Inventory critical: ${p.name} stock level is low (${p.stock} units remaining).`
      });
    });

    // 2. High margin opportunities or recommendation signals
    const highMarginProducts = activeProducts.filter(p => p.current_price > p.cost_price * 1.5);
    highMarginProducts.slice(0, 1).forEach(p => {
      dynamicAlerts.push({
        id: alertId++,
        type: "success",
        message: `Margin healthy: ${p.name} is performing above baseline target thresholds.`
      });
    });

    // 3. General category stats info
    if (activeProducts.length > 0) {
      dynamicAlerts.push({
        id: alertId++,
        type: "info",
        message: `Active monitoring: ${activeProducts.length} SKU categories synced with postgres and mongodb.`
      });
    } else {
      dynamicAlerts.push({
        id: alertId++,
        type: "warning",
        message: "Database synchronizing: no catalog products loaded."
      });
    }

    setAlerts(dynamicAlerts);
  }

  async function handlePricingSubmit(e) {
    e.preventDefault();
    setIsSubmittingPricing(true);
    
    const product = products.find((p) => String(p.id) === String(pricingForm.product));
    if (!product) {
      setIsSubmittingPricing(false);
      showToast("Selected product not found", "error");
      return;
    }

    // Get historical sales
    const productSales = salesInfo.sample.filter(
      (s) => s.product_name === product.name || String(s.product_id) === String(product.id)
    );
    const salesCount = productSales.reduce((acc, s) => acc + (s.quantity_sold || s.units_sold || 0), 0);
    const revenueSum = productSales.reduce((acc, s) => acc + (s.revenue || 0), 0);
    
    const historicalSales = salesCount;
    const historicalRevenue = revenueSum;

    try {
      const response = await axios.get(`${API}/api/ai/recommend-price`, {
        params: {
          current_price: pricingForm.basePrice || product.current_price,
          current_inventory: pricingForm.inventoryLevel || product.stock || 50,
          historical_sales: historicalSales,
          historical_revenue: historicalRevenue,
          stockcode: String(product.id),
          quantity: 10,
          revenue: historicalRevenue,
          competitor_price: pricingForm.competitorPrice
        },
      });

      if (response.data && response.data.status === "success") {
        const rec = response.data.recommendation;
        const newRecommendation = {
          suggestedPrice: rec.recommended_price,
          revenueLift: ((rec.metrics?.revenue_growth_percentage || 0)).toFixed(1),
          confidence: rec.confidence || 85,
          projectedRevenue: Math.round(rec.expected_revenue),
          expectedDemand: rec.expected_demand,
          reason: rec.model_signals || "model pricing signals",
          originalReason: rec.reason,
        };
        
        setRecommendation(newRecommendation);

        // Add to history list
        const newEntry = {
          id: Date.now(),
          product: product.name,
          basePrice: pricingForm.basePrice || product.current_price,
          suggestedPrice: newRecommendation.suggestedPrice,
          timestamp: new Date().toLocaleString(),
          demandLevel: pricingForm.demandLevel,
          inventoryLevel: pricingForm.inventoryLevel,
        };

        const updatedHistory = [newEntry, ...history.slice(0, 9)];
        setHistory(updatedHistory);
        localStorage.setItem("pricingHistory", JSON.stringify(updatedHistory));
        showToast("Price recommendation recalculated.", "success");
      } else {
        showToast("Unable to load pricing data. (Invalid response format)", "error");
      }
    } catch (err) {
      console.error("Pricing submission failed:", err);
      showToast("Unable to load pricing data. Please check backend connection.", "error");
    } finally {
      setIsSubmittingPricing(false);
    }
  }

  function clearHistory() {
    setHistory([]);
    localStorage.removeItem("pricingHistory");
  }

  function resetProductForm() {
    setProductForm({
      id: null,
      name: "",
      category: "",
      current_price: "",
      cost_price: "",
      stock: "",
    });
    setProductMessage({ type: "", text: "" });
  }

  function validateProductForm(form) {
    if (!form.name.trim()) {
      return "Product name is required.";
    }

    if (!form.category.trim()) {
      return "Category is required.";
    }

    const parsedPrice = Number(form.current_price);
    const parsedCost = Number(form.cost_price);
    const parsedStock = Number(form.stock);

    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      return "Current price must be a non-negative number.";
    }

    if (!Number.isFinite(parsedCost) || parsedCost < 0) {
      return "Cost price must be a non-negative number.";
    }

    if (!Number.isInteger(parsedStock) || parsedStock < 0) {
      return "Stock must be a whole number greater than or equal to zero.";
    }

    return "";
  }

  async function submitProductForm(event) {
    event.preventDefault();

    const validationMessage = validateProductForm(productForm);
    if (validationMessage) {
      showToast(validationMessage, "error");
      return;
    }

    setIsSavingProduct(true);

    const payload = {
      name: productForm.name.trim(),
      category: productForm.category.trim(),
      current_price: Number(productForm.current_price || 0),
      cost_price: Number(productForm.cost_price || 0),
      stock: Number(productForm.stock || 0),
    };

    try {
      if (productForm.id) {
        await axios.put(`${API}/products/${productForm.id}`, payload, {
          headers,
        });
        showToast("Product updated successfully.", "success");
      } else {
        await axios.post(`${API}/products`, payload, { headers });
        showToast("Product added successfully.", "success");
      }

      await loadData();
      resetProductForm();
    } catch (error) {
      console.error("Unable to save product", error);
      const detail = error.response?.data?.detail || "Unable to save product.";
      showToast(detail, "error");
    } finally {
      setIsSavingProduct(false);
    }
  }

  function editProduct(product) {
    setProductForm({
      id: product.id,
      name: product.name,
      category: product.category || "",
      current_price: product.current_price ?? "",
      cost_price: product.cost_price ?? "",
      stock: product.stock ?? "",
    });
  }

  async function deleteProduct(productId) {
    if (!window.confirm("Delete this product from the catalog?")) {
      return;
    }

    try {
      await axios.delete(`${API}/products/${productId}`, { headers });
      await loadData();
      if (productForm.id === productId) {
        resetProductForm();
      }
      showToast("Product deleted successfully.", "success");
    } catch (error) {
      console.error("Unable to delete product", error);
      const detail =
        error.response?.data?.detail || "Unable to delete product.";
      showToast(detail, "error");
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    localStorage.removeItem("userRole");
    setToken("");
    setUserName("");
    setUserRole("pricing manager");
    setActiveView("dashboard");
    setActiveAnchor("");
  }

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          const detail = error.response.data?.detail;
          if (detail === "Invalid token" || detail === "User not found") {
            logout();
            showToast("Session expired. Please log in again.", "error");
          }
        }
        return Promise.reject(error);
      }
    );
    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  useEffect(() => {
    if (token) {
      const storedName = localStorage.getItem("userName") || "User";
      const storedRole = getNormalizedRole(
        localStorage.getItem("userRole") || "pricing manager",
      );
      setUserName(storedName);
      setUserRole(storedRole);
      loadData();
    }
  }, [token]);

  useEffect(() => {
    if (!productMessage.text) {
      return;
    }

    const timer = window.setTimeout(() => {
      setProductMessage({ type: "", text: "" });
    }, 3000);

    return () => window.clearTimeout(timer);
  }, [productMessage.text]);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      return;
    }

    const existingScript = document.getElementById("google-gsi");
    
    const initializeGoogle = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCredentialResponse,
        });

        const btnDiv = document.getElementById("google-signin-btn");
        if (btnDiv) {
          window.google.accounts.id.renderButton(btnDiv, {
            theme: "outline",
            size: "large",
            width: "320",
            type: "standard",
            text: "continue_with",
            shape: "rectangular",
          });
        }
        setGoogleReady(true);
      }
    };

    if (existingScript) {
      initializeGoogle();
      return;
    }

    const script = document.createElement("script");
    script.id = "google-gsi";
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      initializeGoogle();
    };
    document.body.appendChild(script);
  }, [GOOGLE_CLIENT_ID, mode]);

  const roleCopy = getRoleCopy(userRole);

  const getRoleActions = (role) => {
    const r = getNormalizedRole(role);
    if (r === "admin") {
      return [
        { label: "Admin Dashboard", type: "view", view: "admin_dashboard" },
        { label: "Executive BI Reports", type: "view", view: "executive_bi" },
        { label: "User & Role Management", type: "view", view: "admin_dashboard" },
        { label: "Products Catalog", type: "view", view: "products" },
        { label: "Pricing Strategy", type: "view", view: "pricing_strategy" },
        { label: "Pricing Comparison", type: "view", view: "pricing_comparison" },
        { label: "Market Intelligence", type: "view", view: "market_intelligence" },
        { label: "Profitability", type: "view", view: "profitability" },
        { label: "Seasonal Trend Reports", type: "view", view: "seasonal_trends" },
        { label: "System/Database Health", type: "view", view: "admin_dashboard" },
        { label: "ML Model Status", type: "view", view: "admin_dashboard" },
        { label: "System Configuration", type: "view", view: "admin_dashboard" },
      ];
    }
    if (r === "pricing manager") {
      return [
        { label: "Pricing Manager", type: "view", view: "pricing_manager_dashboard" },
        { label: "Executive BI Reports", type: "view", view: "executive_bi" },
        { label: "AI Recommendations", type: "view", view: "ai_recommendation" },
        { label: "Pricing Strategy", type: "view", view: "pricing_strategy" },
        { label: "Competitor Monitoring", type: "view", view: "competitor_monitoring" },
        { label: "Pricing Comparison", type: "view", view: "pricing_comparison" },
        { label: "Market Intelligence", type: "view", view: "market_intelligence" },
        { label: "Profitability", type: "view", view: "profitability" },
        { label: "Seasonal Trend Reports", type: "view", view: "seasonal_trends" },
        { label: "Products Catalog", type: "view", view: "products" },
      ];
    }
    if (r === "business analyst") {
      return [
        { label: "Pricing Insights", type: "view", view: "bi_analytics" },
        { label: "AI Recommendations", type: "view", view: "ai_recommendation" },
        { label: "Pricing Strategy", type: "view", view: "pricing_strategy" },
        { label: "Competitor Monitoring", type: "view", view: "competitor_monitoring" },
        { label: "Pricing Comparison", type: "view", view: "pricing_comparison" },
        { label: "Market Intelligence", type: "view", view: "market_intelligence" },
        { label: "Profitability", type: "view", view: "profitability" },
        { label: "Seasonal Trend Reports", type: "view", view: "seasonal_trends" },
        { label: "Products Catalog", type: "view", view: "products" },
      ];
    }
    return [];
  };

  const roleActions = getRoleActions(userRole);

  const roleMetrics =
    getNormalizedRole(userRole) === "business analyst"
      ? [
          {
            label: "Revenue Pulse",
            value: formatCurrency(dashboard?.total_revenue || 0),
            description: "Track portfolio health across all products.",
          },
          {
            label: "Units Sold",
            value: dashboard?.total_units_sold || 0,
            description: "A quick view of conversion intensity.",
          },
          {
            label: "Average Price",
            value: formatCurrency(dashboard?.average_product_price || 0),
            description: "Supports price sensitivity and forecast planning.",
          },
        ]
      : [
          {
            label: "Recommended Revenue Lift",
            value: `${recommendation?.revenueLift || "18.7"}%`,
            description:
              "Based on demand, inventory, and competitor pressure.",
          },
          {
            label: "AI Suggested Price",
            value: formatCurrency(recommendation?.suggestedPrice || 129),
            description: "Real-time pricing recommendation.",
          },
          {
            label: "Forecast Confidence",
            value: `${recommendation?.confidence || "92"}%`,
            description: "Confidence reflects current market conditions.",
          },
        ];

  const showProductsPage = activeView === "products";

  if (!token) {
    return (
      <main className="shell">
        <section
          className="brand-panel"
          aria-label="Revenue intelligence preview"
        >
          <nav className="topbar" aria-label="Product">
            <div className="logo-mark">R</div>
            <span>RevenueIQ</span>
          </nav>

          <div className="hero-copy">
            <p className="eyebrow">
              {mode === "login" ? "AI Pricing Console" : "Access Setup"}
            </p>
            <h1>
              {mode === "login"
                ? "Dynamic Pricing Optimization"
                : "Build your pricing command center"}
            </h1>
            <p>
              {mode === "login"
                ? "Monitor demand signals, competitor movement, inventory pressure, and recommended price actions from one revenue cockpit."
                : "Create a role-based workspace to review revenue signals, pricing recommendations, and forecast-ready market intelligence."}
            </p>
          </div>

          <div className="metrics-grid" aria-label="Revenue metrics">
            <article className="metric primary">
              <span>{mode === "login" ? "Revenue Lift" : "Role Access"}</span>
              <strong>{mode === "login" ? "18.7%" : "3 roles"}</strong>
              <small>
                {mode === "login"
                  ? "Projected this cycle"
                  : "Manager, Analyst, and Admin"}
              </small>
            </article>
            <article className="metric">
              <span>{mode === "login" ? "Optimal Price" : "Role Views"}</span>
              <strong>{mode === "login" ? "₹10,750" : "Tailored"}</strong>
              <small>
                {mode === "login"
                  ? "Recommended SKU avg."
                  : "Each workspace is tuned to the role"}
              </small>
            </article>
            <article className="metric">
              <span>{mode === "login" ? "Demand Index" : "Demo Accounts"}</span>
              <strong>{mode === "login" ? "84" : "3"}</strong>
              <small>
                {mode === "login"
                  ? "High confidence"
                  : "Ready for quick testing"}
              </small>
            </article>
          </div>

          <div className="chart-card" aria-label="Pricing trend chart">
            <div className="chart-head">
              <span>
                {mode === "login" ? "Price Elasticity" : "Role-Based Workspace"}
              </span>
              <strong>{mode === "login" ? "Live model" : "Active"}</strong>
            </div>
            <div className="bars">
              <span style={{ height: "42%" }}></span>
              <span style={{ height: "55%" }}></span>
              <span style={{ height: "48%" }}></span>
              <span style={{ height: "71%" }}></span>
              <span style={{ height: "64%" }}></span>
              <span style={{ height: "82%" }}></span>
              <span style={{ height: "76%" }}></span>
              <span style={{ height: "91%" }}></span>
            </div>
          </div>
        </section>

        <section className="login-panel" aria-label="Login form">
          <form
            className="login-card"
            onSubmit={(e) => {
              e.preventDefault();
              if (mode === "login") login();
              else register();
            }}
          >
            <div>
              <p className="eyebrow">
                {mode === "login" ? "Welcome back" : "Create account"}
              </p>
              <h2>
                {mode === "login"
                  ? "Sign in to your dashboard"
                  : "Register your workspace"}
              </h2>
            </div>

            {mode === "register" && (
              <div className="floating-label-group">
                <input
                  type="text"
                  id="auth-name"
                  placeholder=" "
                  value={auth.name}
                  onChange={(e) => setAuth({ ...auth, name: e.target.value })}
                  required
                />
                <label htmlFor="auth-name">Full name</label>
              </div>
            )}

            <div className="floating-label-group">
              <input
                type="email"
                id="auth-email"
                placeholder=" "
                value={auth.email}
                onChange={(e) => setAuth({ ...auth, email: e.target.value })}
                required
              />
              <label htmlFor="auth-email">Email</label>
            </div>

            <div className="floating-label-group">
              <input
                type="password"
                id="auth-password"
                placeholder=" "
                value={auth.password}
                onChange={(e) => setAuth({ ...auth, password: e.target.value })}
                minLength={mode === "register" ? 6 : undefined}
                required
              />
              <label htmlFor="auth-password">Password</label>
            </div>

            <div className="floating-label-group">
              <select
                id="auth-role"
                value={auth.role}
                onChange={(e) => setAuth({ ...auth, role: e.target.value })}
                required
              >
                {roleOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <label htmlFor="auth-role">{mode === "login" ? "Sign-in role" : "Role"}</label>
            </div>

            {mode === "register" && (
              <div className="floating-label-group">
                <input
                  type="password"
                  id="auth-confirm"
                  placeholder=" "
                  minLength="6"
                  value={auth.confirmPassword}
                  onChange={(e) =>
                    setAuth({ ...auth, confirmPassword: e.target.value })
                  }
                  required
                />
                <label htmlFor="auth-confirm">Confirm password</label>
              </div>
            )}

            {mode === "login" && (
              <div className="row">
                <label className="remember">
                  <input type="checkbox" defaultChecked />
                  Remember me
                </label>
                <a href="#">Forgot password?</a>
              </div>
            )}

            <button type="submit" disabled={isSubmittingAuth}>
              {isSubmittingAuth ? (
                <span className="spinner-btn-content">
                  <span className="spinner-icon"></span>
                  Processing...
                </span>
              ) : (
                mode === "login" ? "Log in" : "Create account"
              )}
            </button>

            <div className="divider">
              <span>or</span>
            </div>

            {GOOGLE_CLIENT_ID ? (
              <div className="google-signin-container">
                <div id="google-signin-btn"></div>
              </div>
            ) : (
              <p className="signup" style={{ textAlign: "center", color: "#ef4444" }}>
                Google Client ID is missing. Configure it in .env.local
              </p>
            )}

            <p className="signup">
              {mode === "login" ? "New analyst?" : "Already registered?"}
              <button
                type="button"
                className="link-button"
                onClick={() => setMode(mode === "login" ? "register" : "login")}
              >
                {mode === "login" ? "Create account" : "Log in"}
              </button>
            </p>
          </form>
        </section>
      </main>
    );
  }

  function isViewAllowed(view, role) {
    const r = getNormalizedRole(role);
    if (view === "dashboard") return true;
    if (r === "admin") {
      return [
        "admin_dashboard", "executive_bi", "products", "ai_monitoring", "prediction_history", 
        "seasonal_trends", "pricing_comparison", "market_intelligence", "profitability", "pricing_strategy"
      ].includes(view);
    }
    if (r === "pricing manager") {
      return [
        "pricing_manager_dashboard", "executive_bi", "ai_recommendation", "products", 
        "seasonal_trends", "competitor_monitoring", "pricing_comparison", 
        "market_intelligence", "profitability", "pricing_strategy"
      ].includes(view);
    }
    if (r === "business analyst") {
      return [
        "business_analyst_dashboard", "bi_analytics", "ai_recommendation", "products", 
        "seasonal_trends", "competitor_monitoring", "pricing_comparison", 
        "market_intelligence", "profitability", "pricing_strategy"
      ].includes(view);
    }
    return false;
  }

  return (
    <div className={`app-container ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="sidebar-brand-wrapper">
          <div className="sidebar-brand">
            <div className="logo-mark">R</div>
            <span className="brand-name">RevenueIQ</span>
          </div>
          <button 
            type="button" 
            className="sidebar-collapse-toggle" 
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            )}
          </button>
        </div>

        <nav className="sidebar-nav">
          {/* Main views group */}
          <div className="nav-group">
            <span className="nav-group-title">Console</span>
            {getNormalizedRole(userRole) !== "admin" && (
              <button
                type="button"
                className={`nav-item ${activeView === "dashboard" && activeAnchor === "" ? "active" : ""}`}
                onClick={() => {
                  setActiveView("dashboard");
                  setActiveAnchor("");
                }}
              >
                {renderNavIcon("dashboard")}
                <span>Dashboard</span>
              </button>
            )}
            {roleActions.filter(action => action.type === "view").map((action) => (
              <button
                key={action.label}
                type="button"
                className={`nav-item ${activeView === action.view ? "active" : ""}`}
                onClick={() => {
                  setActiveView(action.view || "dashboard");
                  setActiveAnchor("");
                }}
              >
                {renderNavIcon(action.label)}
                <span>{action.label}</span>
              </button>
            ))}
          </div>

          {/* Tools & signals group */}
          {roleActions.filter(action => action.type !== "view").length > 0 && (
            <div className="nav-group workspace-group">
              <span className="nav-group-title">Workspace</span>
              {roleActions.filter(action => action.type !== "view").map((action) => (
                <a
                  key={action.label}
                  href={action.href}
                  className={`nav-item ${activeAnchor === action.href ? "active" : ""}`}
                  onClick={() => {
                    setActiveView("dashboard");
                    setActiveAnchor(action.href);
                  }}
                >
                  {renderNavIcon(action.label)}
                  <span>{action.label}</span>
                </a>
              ))}
            </div>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">{userName.charAt(0).toUpperCase()}</div>
            <div className="user-info">
              <span className="user-name">{userName}</span>
              <span className="user-role">{getRoleDisplayName(userRole)}</span>
            </div>
          </div>
          <button 
            className="logout-button" 
            onClick={logout}
            title={sidebarCollapsed ? "Log out" : ""}
          >
            {sidebarCollapsed ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{width: "18px", height: "18px", stroke: "currentColor"}}>
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            ) : "Log out"}
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="dashboard-header">
          <div>
            <h1>{roleCopy.title}</h1>
            <p id="welcomeUser">Welcome back, {userName}. {roleCopy.subtitle}</p>
          </div>
          <div className="header-actions flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 font-medium text-xs flex items-center gap-2 border border-slate-200 dark:border-slate-700 transition cursor-pointer"
              aria-label="Toggle theme"
            >
              {theme === "light" ? (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                  <span>Dark Mode</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M14 12a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span>Light Mode</span>
                </>
              )}
            </button>
            <button
              className="refresh-button cursor-pointer"
              onClick={() => window.location.reload()}
            >
              Refresh Workspace
            </button>
          </div>
        </header>

        {error ? (
          <div className="text-left w-full max-w-xl mx-auto px-4 py-16 text-center space-y-4 animate-fade-in">
            <div className="inline-flex p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400">
              <svg className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Unable to load dashboard data. Please try again.</h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm">{error}</p>
            <button
              onClick={() => { setError(""); loadData(); }}
              className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-xs font-semibold cursor-pointer transition shadow-sm"
            >
              Retry Connection
            </button>
          </div>
        ) : !isViewAllowed(activeView, userRole) ? (
          <div className="text-left w-full max-w-xl mx-auto px-4 py-16 text-center space-y-4 animate-fade-in">
            <div className="inline-flex p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-rose-600 dark:text-rose-400">
              <svg className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Workspace Access Restricted</h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              Your profile is not authorized to access this panel. Dashboards are strictly isolated by enterprise roles.
            </p>
            <button
              onClick={() => setActiveView("dashboard")}
              className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-xs font-semibold cursor-pointer transition shadow-sm"
            >
              Return to my Dashboard
            </button>
          </div>
        ) : isLoadingData ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500 w-full">
            <div className="w-10 h-10 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-4 font-medium">Synchronizing system telemetry...</p>
          </div>
        ) : activeView === "pricing_manager_dashboard" || (activeView === "dashboard" && getNormalizedRole(userRole) === "pricing manager") ? (
          <PricingManagerDashboard
            products={products}
            pricingForm={pricingForm}
            setPricingForm={setPricingForm}
            recommendation={recommendation}
            history={history}
            alerts={alerts}
            formatCurrency={formatCurrency}
            handlePricingSubmit={handlePricingSubmit}
            pricingSearch={pricingSearch}
            setPricingSearch={setPricingSearch}
            pricingSortField={pricingSortField}
            setPricingSortField={setPricingSortField}
            pricingSortOrder={pricingSortOrder}
            setPricingSortOrder={setPricingSortOrder}
            pricingPage={pricingPage}
            setPricingPage={setPricingPage}
            totalPricingPages={totalPricingPages}
            paginatedPricing={paginatedPricing}
            salesSearch={salesSearch}
            setSalesSearch={setSalesSearch}
            salesPage={salesPage}
            setSalesPage={setSalesPage}
            totalSalesPages={totalSalesPages}
            paginatedSales={paginatedSales}
            salesSortField={salesSortField}
            setSalesSortField={setSalesSortField}
            salesSortOrder={salesSortOrder}
            setSalesSortOrder={setSalesSortOrder}
            isSubmittingPricing={isSubmittingPricing}
            clearHistory={clearHistory}
            showToast={showToast}
            loadData={loadData}
          />
        ) : activeView === "business_analyst_dashboard" || (activeView === "dashboard" && getNormalizedRole(userRole) === "business analyst") ? (
          <BusinessAnalystDashboard
            products={products}
            formatCurrency={formatCurrency}
            alerts={alerts}
            salesSearch={salesSearch}
            setSalesSearch={setSalesSearch}
            salesPage={salesPage}
            setSalesPage={setSalesPage}
            totalSalesPages={totalSalesPages}
            paginatedSales={paginatedSales}
            salesSortField={salesSortField}
            setSalesSortField={setSalesSortField}
            salesSortOrder={salesSortOrder}
            setSalesSortOrder={setSalesSortOrder}
          />
        ) : activeView === "admin_dashboard" || (activeView === "dashboard" && getNormalizedRole(userRole) === "admin") ? (
          <AdminDashboard />
        ) : activeView === "ai_dashboard" ? (
          <AIDashboard products={products} salesInfo={salesInfo} />
        ) : activeView === "ai_recommendation" ? (
          <AIRecommendation products={products} salesInfo={salesInfo} userRole={userRole} />
        ) : activeView === "pricing_strategy" ? (
          <PricingStrategyRecommendations
            products={products}
            token={token}
            API={API}
            showToast={showToast}
            formatCurrency={formatCurrency}
          />
        ) : activeView === "seasonal_trends" ? (
          <SeasonalTrendReports products={products} />
        ) : activeView === "competitor_monitoring" ? (
          <CompetitorMonitoring
            products={products}
            token={token}
            API={API}
            setActiveView={setActiveView}
            showToast={showToast}
            formatCurrency={formatCurrency}
          />
        ) : activeView === "pricing_comparison" ? (
          <PricingComparisonReports
            products={products}
            token={token}
            API={API}
            showToast={showToast}
            formatCurrency={formatCurrency}
          />
        ) : activeView === "market_intelligence" ? (
          <MarketIntelligence
            products={products}
            token={token}
            API={API}
            showToast={showToast}
            formatCurrency={formatCurrency}
          />
        ) : activeView === "profitability" ? (
          <ProfitabilityAnalytics
            products={products}
            token={token}
            API={API}
            showToast={showToast}
            formatCurrency={formatCurrency}
          />
        ) : activeView === "executive_bi" ? (
          <ExecutiveBIReports
            products={products}
            token={token}
            API={API}
            showToast={showToast}
            formatCurrency={formatCurrency}
          />
        ) : activeView === "bi_analytics" ? (
          <AnalyticsDashboard products={products} />
        ) : activeView === "ai_monitoring" ? (
          <AIMonitoring />
        ) : activeView === "prediction_history" ? (
          <PredictionHistory />
        ) : activeView === "forecast_visualization" ? (
          <ForecastVisualization />
        ) : activeView === "products" ? (
          <section
            className="product-shell"
            aria-label="Product management page"
          >
            <div className="panel-title panel-title-row">
              <div>
                <p className="eyebrow">Catalog</p>
                <h2>Product Catalog</h2>
              </div>
              <div className="inline-actions">
                <button
                  className="secondary-action compact-button"
                  type="button"
                  onClick={() => setActiveView("dashboard")}
                >
                  Back to dashboard
                </button>
              </div>
            </div>

            <section
              className="tool-panel product-manager-panel"
              aria-label="Product catalog manager"
            >
              <div className="panel-title panel-title-row">
                <div>
                  <p className="eyebrow">Catalog</p>
                  <h2>Manage Products</h2>
                </div>
                {getNormalizedRole(userRole) !== "business analyst" && (
                  <button
                    className="secondary-action compact-button"
                    type="button"
                    onClick={resetProductForm}
                  >
                    New product
                  </button>
                )}
              </div>

              {getNormalizedRole(userRole) !== "business analyst" && (
                <form
                  className="product-manager-grid"
                  onSubmit={submitProductForm}
                >
                  <div className="floating-label-group">
                    <input
                      type="text"
                      id="prod-name"
                      value={productForm.name}
                      onChange={(event) =>
                        setProductForm((prev) => ({
                          ...prev,
                          name: event.target.value,
                        }))
                      }
                      placeholder=" "
                      required
                    />
                    <label htmlFor="prod-name">Product name</label>
                  </div>

                  <div className="floating-label-group">
                    <input
                      type="text"
                      id="prod-category"
                      value={productForm.category}
                      onChange={(event) =>
                        setProductForm((prev) => ({
                          ...prev,
                          category: event.target.value,
                        }))
                      }
                      placeholder=" "
                      required
                    />
                    <label htmlFor="prod-category">Category</label>
                  </div>

                  <div className="floating-label-group">
                    <input
                      type="number"
                      id="prod-price"
                      min="0"
                      value={productForm.current_price}
                      onChange={(event) =>
                        setProductForm((prev) => ({
                          ...prev,
                          current_price: event.target.value,
                        }))
                      }
                      placeholder=" "
                    />
                    <label htmlFor="prod-price">Current price</label>
                  </div>

                  <div className="floating-label-group">
                    <input
                      type="number"
                      id="prod-cost"
                      min="0"
                      value={productForm.cost_price}
                      onChange={(event) =>
                        setProductForm((prev) => ({
                          ...prev,
                          cost_price: event.target.value,
                        }))
                      }
                      placeholder=" "
                    />
                    <label htmlFor="prod-cost">Cost price</label>
                  </div>

                  <div className="floating-label-group">
                    <input
                      type="number"
                      id="prod-stock"
                      min="0"
                      value={productForm.stock}
                      onChange={(event) =>
                        setProductForm((prev) => ({
                          ...prev,
                          stock: event.target.value,
                        }))
                      }
                      placeholder=" "
                    />
                    <label htmlFor="prod-stock">Stock</label>
                  </div>

                  <div className="button-row">
                    <button type="submit" disabled={isSavingProduct}>
                      {isSavingProduct ? (
                        <span className="spinner-btn-content">
                          <span className="spinner-icon"></span>
                          Saving...
                        </span>
                      ) : (
                        productForm.id ? "Update Product" : "Add Product"
                      )}
                    </button>
                    <button
                      className="secondary-action"
                      type="button"
                      onClick={resetProductForm}
                    >
                      Reset
                    </button>
                  </div>
                </form>
              )}

              <div className="table-search-bar">
                <input
                  type="text"
                  placeholder="Search products..."
                  value={catalogSearch}
                  onChange={(e) => {
                    setCatalogSearch(e.target.value);
                    setCatalogPage(1);
                  }}
                  className="table-search-input"
                />
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th onClick={() => {
                        setCatalogSortOrder(catalogSortField === "name" && catalogSortOrder === "asc" ? "desc" : "asc");
                        setCatalogSortField("name");
                      }} style={{ cursor: "pointer" }} className="sortable-header">
                        Product {catalogSortField === "name" ? (catalogSortOrder === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th onClick={() => {
                        setCatalogSortOrder(catalogSortField === "category" && catalogSortOrder === "asc" ? "desc" : "asc");
                        setCatalogSortField("category");
                      }} style={{ cursor: "pointer" }} className="sortable-header">
                        Category {catalogSortField === "category" ? (catalogSortOrder === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th onClick={() => {
                        setCatalogSortOrder(catalogSortField === "current_price" && catalogSortOrder === "asc" ? "desc" : "asc");
                        setCatalogSortField("current_price");
                      }} style={{ cursor: "pointer" }} className="sortable-header">
                        Price {catalogSortField === "current_price" ? (catalogSortOrder === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th onClick={() => {
                        setCatalogSortOrder(catalogSortField === "stock" && catalogSortOrder === "asc" ? "desc" : "asc");
                        setCatalogSortField("stock");
                      }} style={{ cursor: "pointer" }} className="sortable-header">
                        Stock {catalogSortField === "stock" ? (catalogSortOrder === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      {getNormalizedRole(userRole) !== "business analyst" && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedCatalog.length > 0 ? (
                      paginatedCatalog.map((item) => (
                        <tr key={item.id}>
                          <td>{item.name}</td>
                          <td>{item.category}</td>
                          <td>{formatCurrency(item.current_price)}</td>
                          <td>{item.stock}</td>
                          {getNormalizedRole(userRole) !== "business analyst" && (
                            <td>
                              <div className="inline-actions">
                                <button
                                  type="button"
                                  className="link-button compact-button"
                                  onClick={() => editProduct(item)}
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  className="secondary-button compact-button"
                                  onClick={() => deleteProduct(item.id)}
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td
                          colSpan="5"
                          style={{ textAlign: "center", padding: "20px" }}
                        >
                          No products available.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="table-pagination">
                <button
                  type="button"
                  disabled={catalogPage === 1}
                  onClick={() => setCatalogPage(prev => Math.max(prev - 1, 1))}
                  className="pagination-btn"
                >
                  Prev
                </button>
                <span className="pagination-info">Page {catalogPage} of {totalCatalogPages}</span>
                <button
                  type="button"
                  disabled={catalogPage === totalCatalogPages}
                  onClick={() => setCatalogPage(prev => Math.min(prev + 1, totalCatalogPages))}
                  className="pagination-btn"
                >
                  Next
                </button>
              </div>
            </section>
          </section>
        ) : (
          /* General User dashboard overview */
          <div className="text-left w-full max-w-6xl mx-auto px-4 py-6 space-y-6">
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 text-left" aria-label="Dashboard summary">
              {/* Card 1: Total Products */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group hover:-translate-y-1 text-left">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/40 rounded-xl text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">Catalog</span>
                </div>
                <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Products</h3>
                <div className="flex items-baseline gap-2 mt-1">
                  {productsError ? (
                    <span className="text-xs text-rose-500 font-medium">Error loading catalog</span>
                  ) : (
                    <span className="text-2xl font-bold text-slate-900 dark:text-white">{products.length}</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Active items tracked in database</p>
              </div>

              {/* Card 2: Current Revenue */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group hover:-translate-y-1 text-left">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 rounded-xl text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">Baseline</span>
                </div>
                <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">Current Revenue</h3>
                <div className="flex items-baseline gap-2 mt-1">
                  {overviewError ? (
                    <span className="text-xs text-rose-500 font-medium">Error loading revenue</span>
                  ) : !overviewMetrics ? (
                    <span className="text-2xl font-bold text-slate-400">—</span>
                  ) : (
                    <span className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(overviewMetrics.current_revenue)}</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Historical catalog baseline sales</p>
              </div>

              {/* Card 3: Expected Revenue */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group hover:-translate-y-1 text-left">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl text-indigo-600 dark:text-indigo-400 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400">Projected</span>
                </div>
                <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">Expected Revenue</h3>
                <div className="flex items-baseline gap-2 mt-1">
                  {overviewError ? (
                    <span className="text-xs text-rose-500 font-medium">Error loading revenue</span>
                  ) : !overviewMetrics ? (
                    <span className="text-2xl font-bold text-slate-400">—</span>
                  ) : (
                    <span className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(overviewMetrics.expected_revenue)}</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Optimization projected target revenue</p>
              </div>

              {/* Card 4: Revenue Growth % */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group hover:-translate-y-1 text-left">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-cyan-50 dark:bg-cyan-950/40 rounded-xl text-cyan-600 dark:text-cyan-400 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400">Uplift</span>
                </div>
                <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">Revenue Growth %</h3>
                <div className="flex items-baseline gap-2 mt-1">
                  {overviewError ? (
                    <span className="text-xs text-rose-500 font-medium">Error loading lift</span>
                  ) : !overviewMetrics ? (
                    <span className="text-2xl font-bold text-slate-400">—</span>
                  ) : (
                    <span className="text-2xl font-bold text-slate-900 dark:text-white">+{overviewMetrics.revenue_growth_percentage}%</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Relative dynamic price optimization lift</p>
              </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left">
                <div className="border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Activity Outline</span>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white">What Changed</h2>
                </div>
                <ul className="space-y-3.5 text-xs text-slate-600 dark:text-slate-400 font-medium">
                  <li className="flex gap-2"><span>•</span><span>Recent pricing recommendations have been recalculated using the backend LightGBM and Prophet models.</span></li>
                  <li className="flex gap-2"><span>•</span><span>Your session log records are stored locally for comparison. Use the optimizer panels to simulate price headroom.</span></li>
                </ul>
              </section>

              <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm text-left">
                <div className="border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Next Action</span>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white">Recommended Action</h2>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Suggested Next Step</span>
                  <strong className="text-base font-bold text-slate-800 dark:text-slate-200">Review dynamic alerts</strong>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Consult active monitoring metrics in the sidebar to review system logs.</p>
                </div>
              </section>
            </div>
          </div>
        )}
      </main>

      {toast.show && (
        <div className={`toast-notification ${toast.type}`}>
          <span className="toast-icon">
            {toast.type === "success" ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{width: "16px", height: "16px"}}><polyline points="20 6 9 17 4 12"/></svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{width: "16px", height: "16px"}}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            )}
          </span>
          <span className="toast-message">{toast.message}</span>
        </div>
      )}
    </div>
  );
}
