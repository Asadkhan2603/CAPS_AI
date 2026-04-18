import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Fingerprint, Loader } from "lucide-react";

function logBiometricDiagnostic(method, message, error) {
  if (import.meta.env.DEV && typeof console?.[method] === "function") {
    console[method](message, error);
  }
}

/**
 * BiometricLoginButton
 * Displays biometric login option if browser supports WebAuthn
 * Gap-011: Biometric login detection
 */
export const BiometricLoginButton = ({ onBiometricLogin, disabled }) => {
  const [supported, setSupported] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if browser supports WebAuthn
    const checkBiometricSupport = async () => {
      try {
        const available = await window.PublicKeyCredential?.isUserVerifyingPlatformAuthenticatorAvailable?.();
        setSupported(!!available);
      } catch (err) {
        logBiometricDiagnostic("debug", "Biometric not available:", err);
        setSupported(false);
      }
    };

    checkBiometricSupport();
  }, []);

  if (!supported) {
    return null;
  }

  const handleBiometricLogin = async () => {
    setLoading(true);
    try {
      if (onBiometricLogin) {
        await onBiometricLogin();
      }
    } catch (err) {
      logBiometricDiagnostic("error", "Biometric login failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="mt-4"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-gray-500">Or</span>
        </div>
      </div>

      <motion.button
        type="button"
        onClick={handleBiometricLogin}
        disabled={disabled || loading}
        className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-3 border-2 border-purple-200 text-purple-600 rounded-lg hover:bg-purple-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
        whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
      >
        {loading ? (
          <>
            <Loader className="w-5 h-5 animate-spin" />
            Authenticating...
          </>
        ) : (
          <>
            <Fingerprint className="w-5 h-5" />
            Login with Fingerprint
          </>
        )}
      </motion.button>

      <p className="text-xs text-gray-500 text-center mt-2">
        Your biometric data is processed securely on your device
      </p>
    </motion.div>
  );
};

export default BiometricLoginButton;
