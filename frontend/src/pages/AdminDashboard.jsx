import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [healthData, setHealthData] = useState(null);
  const [modelsData, setModelsData] = useState([]);
  const [usersData, setUsersData] = useState(null);

  const [healthError, setHealthError] = useState("");
  const [modelsError, setModelsError] = useState("");
  const [usersError, setUsersError] = useState("");

  const loadAdminTelemetry = async () => {
    setLoading(true);
    setHealthError("");
    setModelsError("");
    setUsersError("");

    // 1. Health
    try {
      const hlRes = await axios.get(`${API}/api/dashboard/health`);
      if (hlRes.data && hlRes.data.status === "success") {
        setHealthData(hlRes.data);
      } else {
        setHealthError("Failed to load health telemetry.");
      }
    } catch (err) {
      console.error("Error loading health telemetry:", err);
      setHealthError("Failed to load health telemetry.");
    }

    // 2. Models
    try {
      const mdRes = await axios.get(`${API}/api/dashboard/models`);
      if (mdRes.data && mdRes.data.status === "success") {
        setModelsData(mdRes.data.registered_models || []);
      } else {
        setModelsError("Failed to load models list.");
      }
    } catch (err) {
      console.error("Error loading models telemetry:", err);
      setModelsError("Failed to load models list.");
    }

    // 3. Users
    try {
      const usRes = await axios.get(`${API}/api/dashboard/users`);
      if (usRes.data && usRes.data.status === "success") {
        setUsersData(usRes.data);
      } else {
        setUsersError("Failed to load user analytics.");
      }
    } catch (err) {
      console.error("Error loading user analytics:", err);
      setUsersError("Failed to load user analytics.");
    }

    setLoading(false);
  };

  useEffect(() => {
    loadAdminTelemetry();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500">
        <div className="w-10 h-10 border-4 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-4 font-medium">Loading dashboard data...</p>
      </div>
    );
  }

  // Check health statuses
  const postgresOk = healthError ? false : healthData?.database_health?.postgres?.connected;
  const mongoOk = healthError ? false : healthData?.database_health?.mongodb?.connected;
  
  let systemHealth = "Healthy";
  if (healthError || !postgresOk || !mongoOk) {
    systemHealth = healthError ? "Error" : "Degraded";
  }

  return (
    <div className="text-left w-full max-w-6xl mx-auto px-4 py-6 space-y-6">
      
      {/* Metrics Section */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">Total Users</span>
          <strong className="text-2xl font-bold text-slate-900 dark:text-white mt-1 block">
            {usersError ? (
              <span className="text-xs text-rose-500 font-medium">Error loading data</span>
            ) : (
              usersData?.total_users || 0
            )}
          </strong>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">Model / System Status</span>
          <div className="mt-1 flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${systemHealth === "Healthy" ? "bg-emerald-500" : systemHealth === "Error" ? "bg-rose-500" : "bg-amber-500 animate-pulse"}`}></span>
            <span className="text-lg font-bold text-slate-900 dark:text-white">
              {healthError ? "Error loading status" : systemHealth}
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">PostgreSQL Status</span>
          <div className="mt-1 flex items-center gap-2">
            {healthError ? (
              <span className="text-xs text-rose-500 font-medium">Error loading status</span>
            ) : (
              <>
                <span className={`w-2.5 h-2.5 rounded-full ${postgresOk ? "bg-emerald-500" : "bg-rose-500"}`}></span>
                <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{postgresOk ? "CONNECTED" : "DISCONNECTED"}</span>
              </>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">MongoDB Status</span>
          <div className="mt-1 flex items-center gap-2">
            {healthError ? (
              <span className="text-xs text-rose-500 font-medium">Error loading status</span>
            ) : (
              <>
                <span className={`w-2.5 h-2.5 rounded-full ${mongoOk ? "bg-emerald-500" : "bg-rose-500"}`}></span>
                <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{mongoOk ? "CONNECTED" : "DISCONNECTED"}</span>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Users & Dataset Telemetry */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Users by Role */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">Users by Role Distribution</h2>
          {usersError ? (
            <p className="text-xs text-rose-500 py-4 font-medium">Failed to load user distribution.</p>
          ) : (
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Admins:</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{usersData?.users_by_role?.admin || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Pricing Managers:</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{usersData?.users_by_role?.pricing_manager || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Business Analysts:</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{usersData?.users_by_role?.business_analyst || 0}</span>
              </div>
            </div>
          )}
        </div>

        {/* Dataset Status */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">Dataset Telemetry Status</h2>
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Online Retail Features File:</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">READY</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Active Registered Models count:</span>
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {modelsError ? (
                  <span className="text-rose-500 font-medium">Error loading</span>
                ) : (
                  modelsData.length
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Active ML Algorithm:</span>
              <span className="font-bold text-violet-600 dark:text-violet-400">LightGBM Regressor</span>
            </div>
          </div>
        </div>
      </section>

      {/* Recent Activity Section */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Recent Registrations */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">Recent User Registrations</h2>
          {usersError ? (
            <p className="text-xs text-rose-500 py-4 font-medium">Failed to load recent users.</p>
          ) : (
            <ul className="space-y-2.5 max-h-56 overflow-y-auto text-xs pr-1">
              {usersData?.recent_users?.length > 0 ? (
                usersData.recent_users.map((u) => (
                  <li key={u.id} className="flex justify-between items-center border-b border-slate-50 dark:border-slate-850 pb-2">
                    <div className="space-y-0.5">
                      <p className="font-semibold text-slate-900 dark:text-white">{u.name}</p>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400">{u.email}</p>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-violet-50 dark:bg-violet-950/20 text-violet-700 dark:text-violet-400 text-[10px] font-bold uppercase">
                      {u.role}
                    </span>
                  </li>
                ))
              ) : (
                <li className="text-center py-6 text-slate-500 dark:text-slate-400">No recent registrations.</li>
              )}
            </ul>
          )}
        </div>

        {/* Recent Audit Logs */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">Recent System Audit logs</h2>
          {healthError ? (
            <p className="text-xs text-rose-500 py-4 font-medium">Failed to load audit logs.</p>
          ) : (
            <ul className="space-y-3 max-h-56 overflow-y-auto text-xs pr-1">
              {healthData?.recent_audit_logs?.length > 0 ? (
                healthData.recent_audit_logs.slice(0, 4).map((log, index) => (
                  <li key={index} className="border-b border-slate-50 dark:border-slate-850 pb-2.5 space-y-0.5">
                    <div className="flex justify-between items-center text-[10px] text-slate-500 dark:text-slate-400">
                      <span className="font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                        {log.event_type || log.event || "SYSTEM"}
                      </span>
                      <span>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ""}</span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                      {log.message || (
                        typeof log.details === "object" && log.details !== null
                          ? Object.entries(log.details).map(([k, v]) => `${k}: ${v}`).join(", ")
                          : log.details
                      )}
                    </p>
                  </li>
                ))
              ) : (
                <li className="text-center py-6 text-slate-500 dark:text-slate-400">No recent system logs.</li>
              )}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
