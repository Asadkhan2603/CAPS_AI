import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Smartphone,
  Laptop,
  Tablet,
  Shield,
  Trash2,
  CheckCircle,
  AlertCircle,
  Clock,
} from "lucide-react";
import { apiClient } from "../../services/apiClient";
import { toast } from "react-hot-toast";

/**
 * SessionManagementPanel
 * Manage active sessions and devices
 * Gap-015: Session management and device control
 */
export const SessionManagementPanel = ({ sessions = [], onSessionTerminated }) => {
  const [terminating, setTerminating] = useState(null);

  const getDeviceIcon = (os) => {
    if (!os) return <Laptop className="w-5 h-5" />;
    const osLower = os.toLowerCase();
    if (osLower.includes("ios")) return <Smartphone className="w-5 h-5" />;
    if (osLower.includes("android")) return <Smartphone className="w-5 h-5" />;
    if (osLower.includes("ipad")) return <Tablet className="w-5 h-5" />;
    return <Laptop className="w-5 h-5" />;
  };

  const formatLastActive = (date) => {
    if (!date) return "Never";
    const now = new Date();
    const diff = now - new Date(date);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (hours < 1) return `${minutes}m ago`;
    if (days < 1) return `${hours}h ago`;
    return `${days}d ago`;
  };

  const handleTerminateSession = async (sessionId) => {
    setTerminating(sessionId);
    try {
      await apiClient.post(`/auth/sessions/${sessionId}/terminate`);
      toast.success("Session terminated");
      if (onSessionTerminated) {
        onSessionTerminated(sessionId);
      }
    } catch (err) {
      toast.error("Failed to terminate session");
    } finally {
      setTerminating(null);
    }
  };

  if (!sessions || sessions.length === 0) {
    return (
      <div className="text-center py-12">
        <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">No active sessions</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sessions.map((session, idx) => (
        <motion.div
          key={session.session_id}
          className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.05 }}
          whileHover={{ scale: 1.01 }}
        >
          <div className="flex items-start justify-between gap-4">
            {/* Device Info */}
            <div className="flex items-start gap-4 flex-1">
              <div className="p-3 bg-gray-100 rounded-lg text-gray-700">
                {getDeviceIcon(session.os)}
              </div>

              <div className="flex-1 min-w-0">
                {/* Header */}
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-gray-900">
                    {session.device_name || "Unknown Device"}
                  </h3>
                  {session.is_current && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">
                      <CheckCircle className="w-3 h-3" />
                      Current
                    </span>
                  )}
                </div>

                {/* OS and Browser */}
                <p className="text-sm text-gray-600 mb-3">
                  {session.browser ? `${session.browser} on ` : ""} {session.os || "Unknown"}
                </p>

                {/* IP and Details */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="font-mono text-gray-700">{session.ip_address}</span>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    Last active {formatLastActive(session.last_active_at)}
                  </div>
                </div>

                {/* Created Date */}
                {session.created_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Added {new Date(session.created_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>

            {/* Actions */}
            {!session.is_current && (
              <motion.button
                onClick={() => handleTerminateSession(session.session_id)}
                disabled={terminating === session.session_id}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                title="Sign out from this device"
              >
                <Trash2 className="w-5 h-5" />
              </motion.button>
            )}
          </div>

          {/* Security Alert */}
          {idx === 0 && sessions.length > 1 && (
            <motion.div
              className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded flex gap-2 text-sm text-blue-700"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <p>Review sessions regularly if you notice unfamiliar devices</p>
            </motion.div>
          )}
        </motion.div>
      ))}
    </div>
  );
};

export default SessionManagementPanel;
