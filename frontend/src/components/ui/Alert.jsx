import { AlertTriangle, X } from 'lucide-react';
import { motion } from 'framer-motion';
import Badge from './Badge';

export default function Alert({ title, message, priority = 'info', onDismiss }) {
  const urgent = priority === 'urgent';
  return (
    <motion.div
      className={`flex items-start gap-3 rounded-2xl border p-4 ${
        urgent
          ? 'border-rose-300 bg-rose-50 text-rose-950 dark:border-rose-500/40 dark:bg-rose-950/55 dark:text-rose-50'
          : 'border-brand-200 bg-brand-50 text-slate-900 dark:border-brand-500/40 dark:bg-slate-900/95 dark:text-slate-50'
      }`}
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <AlertTriangle className={urgent ? 'text-rose-600 dark:text-rose-300' : 'text-brand-600 dark:text-brand-300'} size={18} />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className={`text-sm font-semibold ${urgent ? 'text-rose-700 dark:text-rose-100' : 'text-slate-800 dark:text-slate-50'}`}>{title}</p>
          <Badge variant={urgent ? 'danger' : 'info'}>{priority}</Badge>
        </div>
        <p className={`mt-1 text-sm ${urgent ? 'text-rose-700/90 dark:text-rose-100/85' : 'text-slate-600 dark:text-slate-300'}`}>{message}</p>
      </div>
      {onDismiss ? (
        <button
          className={`inline-flex h-9 w-9 items-center justify-center rounded-xl border transition ${
            urgent
              ? 'border-rose-200 bg-white/80 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-slate-900/80 dark:text-rose-200 dark:hover:bg-rose-950/70'
              : 'border-slate-200 bg-white/80 text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
          }`}
          onClick={onDismiss}
        >
          <X size={14} />
        </button>
      ) : null}
    </motion.div>
  );
}
