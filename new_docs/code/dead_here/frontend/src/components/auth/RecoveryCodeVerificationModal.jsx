import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader, CheckCircle } from "lucide-react";
import { apiClient } from "../../services/apiClient";
import { toast } from "react-hot-toast";

/**
 * RecoveryCodeVerificationModal
 * Modal for entering recovery code during account recovery
 * Gap-010: Recovery code verification (part 2)
 */
export const RecoveryCodeVerificationModal = ({ isOpen, onClose, onSuccess, userId }) => {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await apiClient.post(`/auth/verify-recovery-code/${userId}`, {
        recovery_code: code.trim(),
      });

      if (response.data) {
        setSuccess(true);
        toast.success("Recovery code verified! You can now reset your password.");
        setTimeout(() => {
          onSuccess?.();
          onClose();
        }, 2000);
      }
    } catch (err) {
      setError(
        err.response?.data?.detail || "Invalid recovery code. Please check and try again."
      );
      toast.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-40"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="bg-white rounded-lg shadow-2xl max-w-md w-full p-6"
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Recovery Code</h2>
              <motion.button
                onClick={onClose}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <X className="w-5 h-5 text-gray-600" />
              </motion.button>
            </div>

            {success ? (
              <motion.div
                className="text-center py-8"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
                <p className="text-green-600 font-medium">Recovery code verified!</p>
                <p className="text-gray-600 text-sm mt-2">
                  You can now access your account recovery options.
                </p>
              </motion.div>
            ) : (
              <>
                <p className="text-gray-600 text-sm mb-4">
                  Enter one of your recovery codes to verify you own this account.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-2">
                      Recovery Code
                    </label>
                    <input
                      id="code"
                      type="text"
                      value={code}
                      onChange={(e) => {
                        setCode(e.target.value);
                        setError("");
                      }}
                      placeholder="Enter recovery code"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                      aria-label="Recovery code"
                      disabled={loading}
                    />
                  </div>

                  {error && (
                    <motion.div
                      className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      {error}
                    </motion.div>
                  )}

                  <motion.button
                    type="submit"
                    disabled={!code.trim() || loading}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {loading ? (
                      <>
                        <Loader className="w-4 h-4 animate-spin" />
                        Verifying...
                      </>
                    ) : (
                      "Verify Code"
                    )}
                  </motion.button>
                </form>

                <p className="text-xs text-gray-500 text-center mt-4">
                  Don't have a recovery code? <a href="/auth/recover" className="text-blue-600 hover:underline">
                    Try another recovery method
                  </a>
                </p>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default RecoveryCodeVerificationModal;
