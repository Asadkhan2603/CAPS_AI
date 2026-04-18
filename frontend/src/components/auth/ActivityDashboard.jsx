import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Globe,
  MapPin,
  Smartphone,
  Laptop,
  Tablet,
  Clock,
  AlertTriangle,
  RefreshCw,
  X,
  LogOut,
} from "lucide-react";
import { apiClient, terminateSession } from "../../services/apiClient";
import { useToast } from "../../hooks/useToast";

/**
 * ActivityDashboard
 * Displays login history and account activity
 * Gap-014: Account activity dashboard
 */
export const ActivityDashboard = ({ isOpen, onClose }) => {
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("recent"); // recent, sessions
  const [terminatingSessionId, setTerminatingSessionId] = useState("");
  const { pushToast } = useToast();

  useEffect(() => {
    if (isOpen) {
      fetchActivity();
    }
  }, [isOpen]);

  const fetchActivity = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get('/auth/account-activity/me');
      setActivity(response.data);
    } catch (err) {
      setError("Failed to load activity data");
      pushToast({ title: "Error", description: "Failed to load activity data", variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleTerminateSession = async (sessionId) => {
    if (!sessionId || terminatingSessionId) {
      return;
    }
    setTerminatingSessionId(sessionId);
    try {
      await terminateSession(sessionId);
      pushToast({
        title: "Session signed out",
        description: "That device will need to sign in again.",
        variant: "success",
      });
      await fetchActivity();
    } catch (err) {
      const detail = err?.response?.data?.detail || "Failed to sign out from that device";
      pushToast({ title: "Session sign-out failed", description: detail, variant: "error" });
    } finally {
      setTerminatingSessionId("");
    }
  };

  const getDeviceIcon = (deviceType) => {
    switch (deviceType) {
      case "mobile":
        return <Smartphone className="w-4 h-4" />;
      case "tablet":
        return <Tablet className="w-4 h-4" />;
      default:
        return <Laptop className="w-4 h-4" />;
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return "Unknown";
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (hours < 1) {
      const minutes = Math.floor(diff / 60000);
      return `${minutes}m ago`;
    } else if (hours < 24) {
      return `${hours}h ago`;
    } else if (days < 7) {
      return `${days}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 overflow-y-auto"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="bg-white rounded-lg shadow-2xl max-w-4xl w-full my-8"
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-center p-6 border-b border-gray-200">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Account Activity</h2>
              <p className="text-sm text-gray-600 mt-1">
                Monitor your login activity and manage active sessions
              </p>
            </div>
            <motion.button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <X className="w-6 h-6 text-gray-600" />
            </motion.button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center p-12">
              <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-6 bg-red-50 border border-red-200 rounded m-6 text-red-700">
              {error}
            </div>
          ) : activity ? (
            <>
              {/* Activity Summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6 border-b border-gray-200">
                <motion.div
                  className="bg-blue-50 border border-blue-200 rounded-lg p-4"
                  whileHover={{ scale: 1.02 }}
                >
                  <p className="text-sm text-gray-600">Logins Today</p>
                  <p className="text-3xl font-bold text-blue-600">
                    {activity.login_attempts_today}
                  </p>
                </motion.div>

                <motion.div
                  className="bg-purple-50 border border-purple-200 rounded-lg p-4"
                  whileHover={{ scale: 1.02 }}
                >
                  <p className="text-sm text-gray-600">This Week</p>
                  <p className="text-3xl font-bold text-purple-600">
                    {activity.login_attempts_week}
                  </p>
                </motion.div>

                <motion.div
                  className="bg-orange-50 border border-orange-200 rounded-lg p-4"
                  whileHover={{ scale: 1.02 }}
                >
                  <p className="text-sm text-gray-600">Active Sessions</p>
                  <p className="text-3xl font-bold text-orange-600">
                    {activity.total_sessions}
                  </p>
                </motion.div>
              </div>

              {activity.unusual_activity && (
                <motion.div
                  className="mx-6 mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex gap-3"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-yellow-900">Unusual Activity Detected</p>
                    <p className="text-sm text-yellow-700">
                      We detected a login from a new device or location
                    </p>
                  </div>
                </motion.div>
              )}

              {/* Tabs */}
              <div className="flex border-b border-gray-200 px-6 mt-6">
                <button
                  onClick={() => setActiveTab("recent")}
                  className={`px-4 py-3 font-medium transition-colors ${
                    activeTab === "recent"
                      ? "border-b-2 border-blue-600 text-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Recent Logins
                </button>
                <button
                  onClick={() => setActiveTab("sessions")}
                  className={`px-4 py-3 font-medium transition-colors ${
                    activeTab === "sessions"
                      ? "border-b-2 border-blue-600 text-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Active Sessions
                </button>
              </div>

              {/* Content */}
              <div className="p-6 max-h-96 overflow-y-auto">
                <AnimatePresence mode="wait">
                  {activeTab === "recent" ? (
                    <motion.div
                      key="recent"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="space-y-3"
                    >
                      {activity.recent_logins.length > 0 ? (
                        activity.recent_logins.map((login, idx) => (
                          <motion.div
                            key={idx}
                            className="p-4 bg-gray-50 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                            whileHover={{ scale: 1.02 }}
                          >
                            <div className="flex items-start gap-4">
                              <div className="p-2 bg-white rounded-lg">
                                {getDeviceIcon(login.device_type)}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <p className="font-medium text-gray-900">
                                      {login.browser || "Unknown Browser"}
                                    </p>
                                    <p className="text-sm text-gray-600">
                                      {login.os || "Unknown OS"}
                                    </p>
                                  </div>
                                  <p className="text-sm text-gray-500">
                                    <Clock className="w-4 h-4 inline mr-1" />
                                    {formatTime(login.timestamp)}
                                  </p>
                                </div>
                                <p className="text-sm text-gray-600 mt-2 flex items-center gap-1">
                                  <Globe className="w-4 h-4" />
                                  {login.ip_address || "Unknown IP"}
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        ))
                      ) : (
                        <p className="text-center text-gray-500 py-8">No login history</p>
                      )}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="sessions"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="space-y-3"
                    >
                      {activity.active_sessions.length > 0 ? (
                        activity.active_sessions.map((session, idx) => (
                          <motion.div
                            key={idx}
                            className="p-4 bg-gray-50 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                            whileHover={{ scale: 1.02 }}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-4 flex-1">
                                <div className="p-2 bg-white rounded-lg">
                                  <Laptop className="w-4 h-4 text-gray-600" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium text-gray-900">{session.device_name}</p>
                                  <p className="text-sm text-gray-600">
                                    {session.browser} on {session.os}
                                  </p>
                                  <p className="text-sm text-gray-600 mt-2">
                                    <Globe className="w-4 h-4 inline mr-1" />
                                    {session.ip_address}
                                  </p>
                                  <p className="text-xs text-gray-500 mt-1">
                                    Last active: {formatTime(session.last_active_at)}
                                  </p>
                                </div>
                              </div>
                              {!session.is_current && (
                                <motion.button
                                  onClick={() => handleTerminateSession(session.session_id)}
                                  disabled={terminatingSessionId === session.session_id}
                                  className="px-3 py-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                                  whileHover={{ scale: 1.05 }}
                                  whileTap={{ scale: 0.95 }}
                                  title={terminatingSessionId === session.session_id ? "Signing out..." : "Sign out from this device"}
                                >
                                  {terminatingSessionId === session.session_id ? (
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <LogOut className="w-4 h-4" />
                                  )}
                                </motion.button>
                              )}
                            </div>
                          </motion.div>
                        ))
                      ) : (
                        <p className="text-center text-gray-500 py-8">No active sessions</p>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Footer */}
              <div className="flex justify-between items-center p-6 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  Last login: {activity.last_login ? formatTime(activity.last_login) : "Never"}
                </p>
                <motion.button
                  onClick={fetchActivity}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <RefreshCw className="w-4 h-4" />
                  Refresh
                </motion.button>
              </div>
            </>
          ) : null}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ActivityDashboard;
