"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { PendingApprovalView } from "@/components/PendingApprovalView";
import { AdminUserManagement, PendingUser } from "@/components/AdminUserManagement";
import { OverviewDashboard } from "@/components/OverviewDashboard";
import { ProductCatalog, Product } from "@/components/ProductCatalog";
import { SingleProductPredictionModal } from "@/components/SingleProductPredictionModal";
import { PredictAllModal } from "@/components/PredictAllModal";
import { CompetitorAnalysis } from "@/components/CompetitorAnalysis";
import { RevenueSimulator } from "@/components/RevenueSimulator";
import { useUser } from "@/components/ClerkAuthWrapper";

export default function Home() {
  const clerk = useUser();
  const clerkEmail = clerk?.user?.primaryEmailAddress?.emailAddress;

  // Default User State - Superadmin vaibhavbhagat123455@gmail.com
  const [currentUser, setCurrentUser] = useState({
    email: "vaibhavbhagat123455@gmail.com",
    isApproved: true,
    isAdmin: true
  });

  const [activeTab, setActiveTab] = useState("overview");
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [showPredictAllModal, setShowPredictAllModal] = useState(false);

  // Admin Pending Users State
  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([
    {
      id: "req-101",
      email: "sarah.analytics@enterprise.com",
      name: "Sarah Connor",
      requested_role: "Pricing Manager",
      requested_at: "2026-08-18 14:30",
      status: "pending"
    },
    {
      id: "req-102",
      email: "alex.mercer@retailcorp.io",
      name: "Alex Mercer",
      requested_role: "Business Analyst",
      requested_at: "2026-08-18 15:45",
      status: "pending"
    }
  ]);

  const [approvedEmails, setApprovedEmails] = useState<string[]>([
    "vaibhavbhagat123455@gmail.com"
  ]);

  // Sync with live Clerk user when available
  useEffect(() => {
    if (clerkEmail) {
      if (clerkEmail === "vaibhavbhagat123455@gmail.com") {
        setCurrentUser({
          email: clerkEmail,
          isApproved: true,
          isAdmin: true
        });
      } else {
        const isApproved = approvedEmails.includes(clerkEmail);
        setCurrentUser({
          email: clerkEmail,
          isApproved: isApproved,
          isAdmin: false
        });
        // Register in pending list if new
        if (!isApproved && !pendingUsers.some((u) => u.email === clerkEmail)) {
          setPendingUsers((prev) => [
            {
              id: `req-${Date.now()}`,
              email: clerkEmail,
              name: clerk.user?.fullName || "New User",
              requested_role: "Pricing Analyst",
              requested_at: "Just now",
              status: "pending"
            },
            ...prev
          ]);
        }
      }
    }
  }, [clerkEmail, approvedEmails]);

  useEffect(() => {
    // Fetch product catalog from backend API or local dataset fallback
    fetch("http://127.0.0.1:8000/api/products")
      .then((res) => res.json())
      .then((data) => {
        if (data.products) setProducts(data.products);
      })
      .catch(() => {
        // Fallback catalog matching CSV
        setProducts([
          { id: "prod-1", name: "Wireless Noise-Canceling Headphones", category: "Audio & Electronics", sku: "AUD-WNC-001", current_price: 199.99, cost_price: 110.00, competitor_price: 189.99, competitor_name: "TechGiant Store", inventory: 420, historical_sales_30d: 1250, rating: 4.7, demand_trend: "Increasing", elasticity_score: 1.45, discount_percentage: 5, seasonality_factor: "High (Holiday & Back to School)", last_updated: "2026-08-18" },
          { id: "prod-2", name: "Smart Fitness Watch Ultra", category: "Wearables", sku: "WEAR-SFW-002", current_price: 249.50, cost_price: 135.00, competitor_price: 259.99, competitor_name: "FitLife Direct", inventory: 180, historical_sales_30d: 980, rating: 4.6, demand_trend: "Stable", elasticity_score: 1.20, discount_percentage: 0, seasonality_factor: "Medium", last_updated: "2026-08-18" },
          { id: "prod-3", name: "Ergonomic Mesh Office Chair", category: "Office & Furniture", sku: "FURN-EMC-003", current_price: 329.00, cost_price: 170.00, competitor_price: 349.00, competitor_name: "OfficeDepot Hub", inventory: 75, historical_sales_30d: 410, rating: 4.8, demand_trend: "Increasing", elasticity_score: 0.85, discount_percentage: 10, seasonality_factor: "Constant", last_updated: "2026-08-18" },
          { id: "prod-4", name: "Mechanical Gaming Keyboard RGB", category: "Gaming & PC", sku: "GAME-MGK-004", current_price: 89.99, cost_price: 42.00, competitor_price: 79.99, competitor_name: "CyberGear World", inventory: 610, historical_sales_30d: 2100, rating: 4.5, demand_trend: "Increasing", elasticity_score: 1.70, discount_percentage: 15, seasonality_factor: "High (Q4 Holiday)", last_updated: "2026-08-18" },
          { id: "prod-5", name: "Ultra-Wide 4K Monitor 34-inch", category: "Display & PC", sku: "ELEC-UWM-005", current_price: 499.99, cost_price: 310.00, competitor_price: 529.99, competitor_name: "VisionMarket", inventory: 95, historical_sales_30d: 310, rating: 4.9, demand_trend: "Decreasing", elasticity_score: 1.10, discount_percentage: 0, seasonality_factor: "Medium", last_updated: "2026-08-18" },
          { id: "prod-6", name: "Portable Espresso Coffee Maker", category: "Home Appliances", sku: "HOME-PEC-006", current_price: 74.50, cost_price: 32.00, competitor_price: 69.99, competitor_name: "KitchenBoutique", inventory: 340, historical_sales_30d: 840, rating: 4.4, demand_trend: "Increasing", elasticity_score: 1.60, discount_percentage: 8, seasonality_factor: "High", last_updated: "2026-08-18" },
          { id: "prod-7", name: "Compact Robot Vacuum & Mop", category: "Home Appliances", sku: "HOME-RVM-007", current_price: 389.00, cost_price: 220.00, competitor_price: 399.00, competitor_name: "CleanTech Direct", inventory: 115, historical_sales_30d: 520, rating: 4.6, demand_trend: "Increasing", elasticity_score: 1.35, discount_percentage: 5, seasonality_factor: "High", last_updated: "2026-08-18" },
          { id: "prod-8", name: "Pro Studio Condenser Microphone", category: "Audio & Electronics", sku: "AUD-PCM-008", current_price: 149.00, cost_price: 68.00, competitor_price: 159.00, competitor_name: "AudioStream Pro", inventory: 260, historical_sales_30d: 730, rating: 4.8, demand_trend: "Stable", elasticity_score: 1.05, discount_percentage: 0, seasonality_factor: "Medium", last_updated: "2026-08-18" },
          { id: "prod-9", name: "Smart Ambient LED Desk Lamp", category: "Office & Furniture", sku: "FURN-SAL-009", current_price: 49.99, cost_price: 18.50, competitor_price: 44.99, competitor_name: "Lumino Living", inventory: 510, historical_sales_30d: 1640, rating: 4.5, demand_trend: "Increasing", elasticity_score: 1.80, discount_percentage: 10, seasonality_factor: "High", last_updated: "2026-08-18" },
          { id: "prod-10", name: "Dual Wireless Fast Charging Station", category: "Audio & Electronics", sku: "ELEC-WCS-010", current_price: 39.99, cost_price: 14.00, competitor_price: 42.50, competitor_name: "PowerHub Supply", inventory: 820, historical_sales_30d: 2450, rating: 4.6, demand_trend: "Stable", elasticity_score: 1.50, discount_percentage: 12, seasonality_factor: "High", last_updated: "2026-08-18" }
        ]);
      });
  }, []);

  const handleApproveUser = (id: string, email: string) => {
    setPendingUsers((prev) => prev.filter((u) => u.id !== id));
    if (!approvedEmails.includes(email)) {
      setApprovedEmails((prev) => [...prev, email]);
    }
  };

  const handleRejectUser = (id: string) => {
    setPendingUsers((prev) => prev.filter((u) => u.id !== id));
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Navigation Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentUser={currentUser}
        setCurrentUser={setCurrentUser}
        pendingCount={pendingUsers.length}
      />

      {/* Main Content Body */}
      <main className="flex-1 pb-16">
        {!currentUser.isApproved ? (
          <PendingApprovalView
            currentUser={currentUser}
            onSwitchToAdmin={() =>
              setCurrentUser({
                email: "vaibhavbhagat123455@gmail.com",
                isApproved: true,
                isAdmin: true
              })
            }
          />
        ) : (
          <>
            {activeTab === "overview" && (
              <OverviewDashboard
                onNavigateToCatalog={() => setActiveTab("products")}
              />
            )}

            {activeTab === "products" && (
              <ProductCatalog
                products={products}
                onPredictSingle={(product) => setSelectedProduct(product)}
                onPredictAll={() => setShowPredictAllModal(true)}
              />
            )}

            {activeTab === "competitors" && <CompetitorAnalysis />}

            {activeTab === "simulator" && <RevenueSimulator products={products} />}

            {activeTab === "admin" && currentUser.isAdmin && (
              <AdminUserManagement
                pendingUsers={pendingUsers}
                approvedEmails={approvedEmails}
                onApproveUser={handleApproveUser}
                onRejectUser={handleRejectUser}
              />
            )}
          </>
        )}
      </main>

      {/* Modals */}
      {selectedProduct && (
        <SingleProductPredictionModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
        />
      )}

      {showPredictAllModal && (
        <PredictAllModal
          products={products}
          onClose={() => setShowPredictAllModal(false)}
        />
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
          <p>© 2026 PricePilot AI — Dynamic Pricing Optimization & Revenue Intelligence System</p>
          <div className="flex items-center gap-4">
            <span>Admin: vaibhavbhagat123455@gmail.com</span>
            <span>Models: LightGBM, XGBoost, Prophet</span>
            <span>Agents: OpenRouter + Tavily + News API</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
