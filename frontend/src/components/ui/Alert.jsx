import { AlertTriangle, X } from 'lucide-react';
import { motion } from 'framer-motion';
import Badge from './Badge';

export default function Alert({ title, message, priority = 'info', onDismiss }) {
  const urgent = priority === 'urgent';
  return (
    <motion.div
      className={`flex items-start gap-3 rounded-2xl border p-4 ${urgent ? 'border-rose-300 bg-rose-50 dark:border-rose-800 dark:bg-rose-900/20' : 'border-brand-200 bg-brand-50 dark:border-brand-800 dark:bg-brand-900/20'}`}
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <AlertTriangle className={urgent ? 'text-rose-600' : 'text-brand-600'} size={18} />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold">{title}</p>
          <Badge variant={urgent ? 'danger' : 'info'}>{priority}</Badge>
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{message}</p>
      </div>
      {onDismiss ? (
        <button className="btn-secondary !p-1.5" onClick={onDismiss}>
          <X size={14} />
        </button>
      ) : null}
    </motion.div>
  );
}
