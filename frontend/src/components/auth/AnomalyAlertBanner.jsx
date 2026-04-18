import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, X, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * AnomalyAlertBanner - Displays security alerts for unusual login activity
 * Shows alerts for new devices or new network locations
 */
export function AnomalyAlertBanner({ anomaly, onDismiss, onReviewActivity, onSecureAccount, floating = false }) {
  const [isVisible, setIsVisible] = useState(Boolean(anomaly));
  const autoHideTimerRef = useRef(null);

  const handleDismiss = useCallback(() => {
    setIsVisible(false);
    if (autoHideTimerRef.current) {
      clearTimeout(autoHideTimerRef.current);
      autoHideTimerRef.current = null;
    }
    onDismiss?.();
  }, [onDismiss]);

  useEffect(() => {
    if (anomaly) {
      setIsVisible(true);
    }
  }, [anomaly]);

  useEffect(() => {
    if (!anomaly || !isVisible) {
      if (autoHideTimerRef.current) {
        clearTimeout(autoHideTimerRef.current);
        autoHideTimerRef.current = null;
      }
      return;
    }

    autoHideTimerRef.current = setTimeout(() => {
      setIsVisible(false);
      autoHideTimerRef.current = null;
    }, 8000);

    return () => {
      if (autoHideTimerRef.current) {
        clearTimeout(autoHideTimerRef.current);
        autoHideTimerRef.current = null;
      }
    };
  }, [anomaly, isVisible]);

  if (!anomaly?.new_device && !anomaly?.new_network) {
    return null;
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -20, height: 0 }}
          transition={{ duration: 0.3 }}
          data-testid="anomaly-alert-banner"
          className={[
            'overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-orange-500/10 backdrop-blur-md',
            floating
              ? 'fixed left-1/2 top-4 z-30 w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 shadow-[0_18px_60px_-30px_rgba(251,191,36,0.45)]'
              : 'mx-4 mt-4'
          ].join(' ')}
        >
          <div className="flex gap-3 px-4 py-3 sm:px-5 sm:py-4">
            <div className="flex-shrink-0 pt-0.5">
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
              >
                <AlertTriangle size={20} className="text-amber-500" />
              </motion.div>
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold text-amber-200">Unusual Activity Detected</h3>
              <div className="mt-1 space-y-0.5 text-xs text-amber-100/80">
                {anomaly.new_device && (
                  <div className="flex items-center gap-1.5">
                    <Shield size={14} />
                    <span>New device logged in from your account</span>
                  </div>
                )}
                {anomaly.new_network && (
                  <div className="flex items-center gap-1.5">
                    <Shield size={14} />
                    <span>Login from a new location</span>
                  </div>
                )}
              </div>
              {anomaly.message && (
                <p className="mt-2 text-xs text-amber-100 leading-relaxed">
                  {anomaly.message}
                </p>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onReviewActivity}
                  className="inline-flex items-center gap-1 rounded-lg bg-amber-500/20 px-2.5 py-1 text-xs font-medium text-amber-300 transition-colors hover:bg-amber-500/30"
                >
                  Review Activity
                </button>
                <button
                  type="button"
                  onClick={onSecureAccount}
                  className="inline-flex items-center gap-1 rounded-lg bg-red-500/20 px-2.5 py-1 text-xs font-medium text-red-300 transition-colors hover:bg-red-500/30"
                >
                  Secure Account
                </button>
              </div>
            </div>

            <button
              type="button"
              onClick={handleDismiss}
              className="flex-shrink-0 p-1 rounded-lg transition-colors hover:bg-white/10 text-amber-200 hover:text-amber-100"
            >
              <X size={18} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * useAnomalyAlert - Hook to manage anomaly alert state
 */
export function useAnomalyAlert() {
  const [anomaly, setAnomaly] = useState(null);

  const showAnomaly = (anomalyData) => {
    if (anomalyData?.new_device || anomalyData?.new_network) {
      setAnomaly(anomalyData);
    }
  };

  const clearAnomaly = () => {
    setAnomaly(null);
  };

  return { anomaly, showAnomaly, clearAnomaly };
}
