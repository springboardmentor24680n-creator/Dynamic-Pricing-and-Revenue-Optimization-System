/**
 * PricePilot AI - Feature Flags Configuration
 * 
 * Controls which features are visible/accessible in the UI.
 * Backend APIs remain intact regardless of flag state.
 */
const FEATURES = {
  // Core - Always active
  DASHBOARD: true,
  PRODUCTS: true,
  PRICING: true,
  DATASETS: true,
  USERS: true,
  SETTINGS: true,
  ACCESS_REQUESTS: true,

  // Enterprise modules - Active
  AI_PRICING: true,
  RECOMMENDATIONS: true,
  REPORTS: true,
  PROFITABILITY: true,
  PRICING_STRATEGY: true,
  EXECUTIVE_BI: true,
  ANALYTICS: true,
  REVENUE_INTELLIGENCE: true,

  // Reserved for future milestones
  FORECASTING: false,
  ADVANCED_ANALYTICS: false,
  BUSINESS_INTELLIGENCE: false,
  PREDICTIVE_INSIGHTS: false,
};

/**
 * Check if a feature is enabled.
 * @param {string} feature - Feature key from FEATURES object
 * @returns {boolean}
 */
export function isFeatureEnabled(feature) {
  return FEATURES[feature] === true;
}

/**
 * Get all enabled features as a list of keys.
 * @returns {string[]}
 */
export function getEnabledFeatures() {
  return Object.entries(FEATURES)
    .filter(([, enabled]) => enabled)
    .map(([key]) => key);
}

/**
 * Get sidebar navigation items based on enabled features.
 * @returns {Array<{label: string, path: string, icon: string, feature: string}>}
 */
export function getSidebarItems() {
  const items = [
    { label: 'Dashboard', path: '/dashboard', icon: 'LayoutDashboard', feature: 'DASHBOARD' },
    { label: 'Product Management', path: '/products', icon: 'Package', feature: 'PRODUCTS' },
    { label: 'Pricing Management', path: '/pricing', icon: 'DollarSign', feature: 'PRICING' },
    { label: 'AI Price Prediction', path: '/ai', icon: 'BrainCircuit', feature: 'AI_PRICING' },
    { label: 'Dataset Management', path: '/datasets', icon: 'Database', feature: 'DATASETS' },
    { label: 'Reports', path: '/reports', icon: 'BarChart3', feature: 'REPORTS' },
    { label: 'Profitability', path: '/profitability', icon: 'TrendingUp', feature: 'PROFITABILITY' },
    { label: 'Pricing Strategy', path: '/pricing-strategy', icon: 'Target', feature: 'PRICING_STRATEGY' },
    { label: 'Executive BI', path: '/executive-bi', icon: 'LayoutDashboard', feature: 'EXECUTIVE_BI' },
    { label: 'User Management', path: '/users', icon: 'Users', feature: 'USERS', adminOnly: true },
    { label: 'Access Requests', path: '/access-requests', icon: 'UserCheck', feature: 'ACCESS_REQUESTS', adminOnly: true },
    { label: 'Settings', path: '/settings', icon: 'Settings', feature: 'SETTINGS' },
  ];

  return items.filter((item) => FEATURES[item.feature]);
}

export default FEATURES;
