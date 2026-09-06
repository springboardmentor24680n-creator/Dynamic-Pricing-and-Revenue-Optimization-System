"use client";

import React, { useState } from "react";
import { ShieldCheck, UserCheck, UserX, Clock, Mail, CheckCircle2, AlertCircle } from "lucide-react";

export interface PendingUser {
  id: string;
  email: string;
  name: string;
  requested_role: string;
  requested_at: string;
  status: string;
}

interface AdminUserManagementProps {
  pendingUsers: PendingUser[];
  approvedEmails: string[];
  onApproveUser: (id: string, email: string) => void;
  onRejectUser: (id: string) => void;
}

export const AdminUserManagement: React.FC<AdminUserManagementProps> = ({
  pendingUsers,
  approvedEmails,
  onApproveUser,
  onRejectUser
}) => {
  const [notification, setNotification] = useState<string | null>(null);

  const handleApprove = (id: string, email: string) => {
    onApproveUser(id, email);
    setNotification(`Approved access for ${email}!`);
    setTimeout(() => setNotification(null), 4000);
  };

  const handleReject = (id: string, email: string) => {
    onRejectUser(id);
    setNotification(`Rejected request from ${email}.`);
    setTimeout(() => setNotification(null), 4000);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl p-6 shadow-md border border-slate-700 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold mb-2">
            <ShieldCheck className="w-4 h-4" />
            Superadmin Security Portal
          </div>
          <h2 className="text-2xl font-bold tracking-tight">
            User Access Request & Authorization Management
          </h2>
          <p className="text-slate-300 text-xs mt-1">
            Superadmin Email: <strong className="text-white font-mono">vaibhavbhagat123455@gmail.com</strong>
          </p>
        </div>

        <div className="flex items-center gap-4 bg-slate-800/80 px-4 py-3 rounded-xl border border-slate-700">
          <div className="text-right">
            <p className="text-xs text-slate-400 font-medium">Pending Requests</p>
            <p className="text-2xl font-bold text-amber-400">{pendingUsers.length}</p>
          </div>
          <div className="h-8 w-px bg-slate-700" />
          <div className="text-right">
            <p className="text-xs text-slate-400 font-medium">Approved Users</p>
            <p className="text-2xl font-bold text-emerald-400">{approvedEmails.length}</p>
          </div>
        </div>
      </div>

      {notification && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 shadow-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          {notification}
        </div>
      )}

      {/* Pending User Requests Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-500" />
              Pending Registration Requests ({pendingUsers.length})
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Review non-admin users waiting for dynamic pricing platform authorization.
            </p>
          </div>
        </div>

        {pendingUsers.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto opacity-80" />
            <p className="font-semibold text-slate-800">No Pending Access Requests</p>
            <p className="text-xs">All user registration requests have been authenticated and verified.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 font-semibold text-xs border-b border-slate-200 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3.5">User / Email</th>
                  <th className="px-6 py-3.5">Requested Role</th>
                  <th className="px-6 py-3.5">Requested Time</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pendingUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-700 text-xs">
                          {user.name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-bold text-slate-900">{user.name}</p>
                          <p className="text-xs text-slate-500 font-mono flex items-center gap-1">
                            <Mail className="w-3 h-3 text-slate-400" />
                            {user.email}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4 font-medium text-slate-700">
                      <span className="bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md text-xs font-semibold border border-slate-200">
                        {user.requested_role}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-xs text-slate-500 font-medium">
                      {user.requested_at}
                    </td>

                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        <Clock className="w-3 h-3" />
                        Pending Approval
                      </span>
                    </td>

                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => handleApprove(user.id, user.email)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1 shadow-sm"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        Approve & Authenticate
                      </button>

                      <button
                        onClick={() => handleReject(user.id, user.email)}
                        className="bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-700 border border-slate-200 hover:border-rose-200 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1"
                      >
                        <UserX className="w-3.5 h-3.5" />
                        Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Approved Users List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2 mb-4">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          Active Authenticated Users ({approvedEmails.length})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {approvedEmails.map((email, idx) => (
            <div
              key={idx}
              className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs"
            >
              <div className="flex items-center gap-2 font-mono text-slate-800 font-semibold truncate">
                <Mail className="w-3.5 h-3.5 text-brand-600 shrink-0" />
                <span className="truncate">{email}</span>
              </div>
              {email === "vaibhavbhagat123455@gmail.com" ? (
                <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded shrink-0">
                  Super Admin
                </span>
              ) : (
                <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded shrink-0">
                  Approved
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
