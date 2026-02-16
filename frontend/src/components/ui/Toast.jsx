import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const icons = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info
};

const tones = {
  success: 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-100',
  error: 'border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-100',
  info: 'border-brand-300 bg-brand-50 text-brand-900 dark:border-brand-800 dark:bg-brand-900/30 dark:text-brand-100'
};

export default function Toast({ toasts, onDismiss }) {
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[70] space-y-3">
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = icons[toast.variant] ?? Info;
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 32 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 32 }}
              className={`pointer-events-auto w-80 rounded-2xl border p-4 shadow-soft ${tones[toast.variant] || tones.info}`}
            >
              <div className="flex items-start gap-3">
                <Icon size={18} className="mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold">{toast.title}</p>
                  {toast.description ? <p className="mt-1 text-xs opacity-90">{toast.description}</p> : null}
                </div>
                <button className="btn-secondary !p-1.5" onClick={() => onDismiss(toast.id)}>
                  <X size={14} />
                </button>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
