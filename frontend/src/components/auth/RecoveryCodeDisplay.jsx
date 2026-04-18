import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Copy, Download, Check, AlertTriangle } from "lucide-react";

/**
 * RecoveryCodeDisplay
 * Displays recovery codes for account backup and allows user to copy/download them.
 * Gap-010: Recovery code verification UI (part 1)
 */
export const RecoveryCodeDisplay = ({ codes, generatedAt, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  if (!codes || codes.length === 0) {
    return null;
  }

  const copyToClipboard = () => {
    const text = codes.join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const downloadCodes = () => {
    const content = [
      "Recovery Codes for CAPS AI Portal",
      `Generated: ${new Date(generatedAt).toLocaleString()}`,
      "",
      "!!WARNING!! Store these codes securely. Each code can be used only ONCE to recover your account.",
      "",
      codes.map((code, idx) => `${idx + 1}. ${code}`).join("\n"),
      "",
      "If you lose these codes, generate new ones in account settings.",
    ].join("\n");

    const blob = new Blob([content], { type: "text/plain" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `recovery-codes-${Date.now()}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);

    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 3000);
  };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="bg-white rounded-lg shadow-2xl max-w-2xl w-full p-6"
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start gap-3 mb-6">
            <div className="bg-yellow-100 rounded-lg p-3">
              <AlertTriangle className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-bold text-gray-900">Recovery Codes</h2>
              <p className="text-sm text-gray-600 mt-1">
                Save these codes securely. You'll need them if you lose access to your account.
              </p>
            </div>
          </div>

          {/* Warning */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-yellow-800">
              <strong>⚠️ Each code can only be used ONCE.</strong> Store them in a secure location like a password manager or printed document.
            </p>
          </div>

          {/* Codes Grid */}
          <div className="grid grid-cols-2 gap-3 mb-6 max-h-64 overflow-y-auto bg-gray-50 p-4 rounded-lg">
            {codes.map((code, idx) => (
              <div
                key={idx}
                className="bg-white border border-gray-200 rounded p-3 font-mono text-sm text-gray-700"
              >
                {idx + 1}. <span className="font-bold text-gray-900">{code}</span>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mb-6">
            <motion.button
              onClick={copyToClipboard}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy All
                </>
              )}
            </motion.button>

            <motion.button
              onClick={downloadCodes}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {downloaded ? (
                <>
                  <Check className="w-4 h-4" />
                  Downloaded!
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Download
                </>
              )}
            </motion.button>
          </div>

          {/* Confirmation Checkbox */}
          <label className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg mb-6 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 rounded text-blue-600" required />
            <span className="text-sm text-blue-900">
              I have saved my recovery codes in a secure location
            </span>
          </label>

          {/* Close Button */}
          <motion.button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            I've Saved My Codes
          </motion.button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default RecoveryCodeDisplay;
