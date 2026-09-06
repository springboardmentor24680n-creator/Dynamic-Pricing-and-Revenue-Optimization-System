"use client";

import React from "react";
import { 
  TrendingUp, 
  Layers, 
  BarChart3, 
  Users, 
  Search, 
  Newspaper, 
  BrainCircuit, 
  ShieldCheck, 
  UserCheck, 
  SlidersHorizontal, 
  Sparkles,
  LogIn
} from "lucide-react";
import { SignInButton, SignedIn, SignedOut, UserButton } from "./ClerkAuthWrapper";

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  currentUser: { email: string; isApproved: boolean; isAdmin: boolean };
  setCurrentUser: (user: { email: string; isApproved: boolean; isAdmin: boolean }) => void;
  pendingCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  currentUser,
  setCurrentUser,
  pendingCount
}) => {
  const toggleDemoUser = () => {
    if (currentUser.isAdmin) {
      setCurrentUser({
        email: "alex.mercer@retailcorp.io",
        isApproved: false,
        isAdmin: false
      });
    } else {
      setCurrentUser({
        email: "vaibhavbhagat123455@gmail.com",
        isApproved: true,
        isAdmin: true
      });
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-subtle">
      {/* Top Banner with AI System Status & Admin Controls */}
      <div className="bg-slate-900 text-slate-100 text-xs px-6 py-2 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-blue-400 font-medium">
            <BrainCircuit className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
            <span>Master AI: <strong className="text-white">openai/gpt-oss-20b:free</strong></span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <Search className="w-3.5 h-3.5 text-emerald-400" />
            <span>Search Agent: <strong className="text-white">Tavily Engine (Live Connected)</strong></span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-amber-400 font-medium">
            <Newspaper className="w-3.5 h-3.5 text-amber-400" />
            <span>News Agent: <strong className="text-white">News API (Live Connected)</strong></span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-purple-400 font-medium">
            <Layers className="w-3.5 h-3.5 text-purple-400" />
            <span>ML Models: <strong className="text-white">LightGBM, XGBoost, Prophet</strong></span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Clerk Auth Integration Widget */}
          <div className="flex items-center gap-2">
            <SignedIn>
              <div className="flex items-center gap-2 bg-slate-800 px-2 py-1 rounded-md border border-slate-700">
                <span className="text-[11px] text-slate-300">Clerk Active:</span>
                <UserButton afterSignOutUrl="/" />
              </div>
            </SignedIn>
            <SignedOut>
              <SignInButton mode="modal">
                <button className="bg-brand-600 hover:bg-brand-700 text-white font-semibold px-2.5 py-1 rounded-md transition-all text-xs flex items-center gap-1 shadow-sm">
                  <LogIn className="w-3 h-3" />
                  Sign In with Clerk
                </button>
              </SignInButton>
            </SignedOut>
          </div>

          <div className="flex items-center gap-2 bg-slate-800 px-2.5 py-1 rounded-md border border-slate-700">
            {currentUser.isAdmin ? (
              <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                Super Admin ({currentUser.email})
              </span>
            ) : currentUser.isApproved ? (
              <span className="flex items-center gap-1 text-blue-400 font-semibold">
                <UserCheck className="w-3.5 h-3.5" />
                Approved Analyst ({currentUser.email})
              </span>
            ) : (
              <span className="flex items-center gap-1 text-amber-400 font-semibold">
                <Users className="w-3.5 h-3.5" />
                Pending Approval ({currentUser.email})
              </span>
            )}
          </div>

          <button
            onClick={toggleDemoUser}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 font-medium px-2.5 py-1 rounded-md transition-all text-xs flex items-center gap-1 shadow-sm"
            title="Toggle between Superadmin vaibhavbhagat123455@gmail.com and a Pending Non-Admin Account for testing"
          >
            <Sparkles className="w-3 h-3 text-amber-300" />
            {currentUser.isAdmin ? "Test Pending Non-Admin View" : "Switch to Admin (vaibhavbhagat123455@gmail.com)"}
          </button>
        </div>
      </div>

      {/* Main Navigation Header */}
      <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              PricePilot AI
              <span className="text-xs bg-brand-50 text-brand-700 border border-brand-200 font-semibold px-2 py-0.5 rounded-full">
                Revenue Intelligence v1.0
              </span>
            </h1>
            <p className="text-xs text-slate-500 font-medium">
              Dynamic Pricing Optimization & Multi-Agent Market Intelligence
            </p>
          </div>
        </div>

        {/* Primary Tabs */}
        {currentUser.isApproved && (
          <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-sm font-medium">
            <button
              onClick={() => setActiveTab("overview")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "overview"
                  ? "bg-white text-brand-600 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              Overview & Analytics
            </button>

            <button
              onClick={() => setActiveTab("products")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "products"
                  ? "bg-white text-brand-600 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              <Layers className="w-4 h-4" />
              Catalog & Predictions
            </button>

            <button
              onClick={() => setActiveTab("competitors")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "competitors"
                  ? "bg-white text-brand-600 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              <Search className="w-4 h-4" />
              Competitor Analysis
            </button>

            <button
              onClick={() => setActiveTab("simulator")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "simulator"
                  ? "bg-white text-brand-600 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
              Revenue Simulator
            </button>

            {currentUser.isAdmin && (
              <button
                onClick={() => setActiveTab("admin")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all relative ${
                  activeTab === "admin"
                    ? "bg-white text-brand-600 shadow-sm font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
              >
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                User Approvals
                {pendingCount > 0 && (
                  <span className="bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full ml-1">
                    {pendingCount}
                  </span>
                )}
              </button>
            )}
          </nav>
        )}
      </div>
    </header>
  );
};
