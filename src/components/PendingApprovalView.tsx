"use client";

import React, { useState } from "react";
import { Clock, ShieldAlert, CheckCircle2, Mail, ArrowRight, UserCheck, Sparkles } from "lucide-react";

interface PendingApprovalProps {
  currentUser: { email: string; isApproved: boolean; isAdmin: boolean };
  onSwitchToAdmin: () => void;
}

export const PendingApprovalView: React.FC<PendingApprovalProps> = ({
  currentUser,
  onSwitchToAdmin
}) => {
  const [requested, setRequested] = useState(false);

  const handleRequestAccess = () => {
    setRequested(true);
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="max-w-xl w-full bg-white rounded-2xl border border-slate-200 shadow-card p-8 text-center relative overflow-hidden">
        {/* Decorative Light Background Elements */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-amber-50 rounded-full blur-2xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-brand-50 rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10">
          <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-sm border border-amber-200">
            <Clock className="w-8 h-8 animate-pulse" />
          </div>

          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200 mb-3">
            <ShieldAlert className="w-3.5 h-3.5" />
            Access Pending Superadmin Approval
          </span>

          <h2 className="text-2xl font-bold text-slate-900 mb-3 tracking-tight">
            User Registration Pending
          </h2>

          <p className="text-slate-600 text-sm mb-6 leading-relaxed">
            Your account (<strong className="text-slate-900 font-semibold">{currentUser.email}</strong>) has been successfully created via Clerk Auth and stored in the <strong className="text-slate-900 font-semibold">Pending Requests Queue</strong>.
          </p>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-left mb-6 text-xs text-slate-700 space-y-2">
            <div className="flex items-center gap-2 text-slate-900 font-semibold text-sm pb-1 border-b border-slate-200">
              <Mail className="w-4 h-4 text-brand-600" />
              Role-Based Security Protocol
            </div>
            <p className="text-slate-600">
              The primary administrator for this PricePilot AI system is:
            </p>
            <div className="bg-white border border-brand-200 text-brand-700 font-mono font-bold px-3 py-2 rounded-lg text-xs flex items-center justify-between shadow-subtle">
              <span>vaibhavbhagat123455@gmail.com</span>
              <span className="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded font-sans">
                Super Admin
              </span>
            </div>
            <p className="text-slate-500 text-[11px] pt-1">
              Once the administrator reviews and approves your request, full access to the Price Prediction, Multi-Agent Engine, and Demand Reports will be unlocked automatically.
            </p>
          </div>

          <div className="space-y-3">
            {!requested ? (
              <button
                onClick={handleRequestAccess}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 shadow-sm text-sm"
              >
                Send Access Reminder to Admin
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Access notification dispatched to vaibhavbhagat123455@gmail.com!
              </div>
            )}

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-white text-slate-400 font-medium">Developer & Demo Options</span>
              </div>
            </div>

            <button
              onClick={onSwitchToAdmin}
              className="w-full bg-brand-50 hover:bg-brand-100 text-brand-700 border border-brand-200 font-semibold py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-sm shadow-subtle"
            >
              <Sparkles className="w-4 h-4 text-brand-600" />
              Switch Account to Super Admin (vaibhavbhagat123455@gmail.com)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
