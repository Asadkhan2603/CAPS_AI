import { X } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export default function Modal({ open, title, onClose, children, size = 'default' }) {
  const contentClassName =
    size === 'large'
      ? 'max-w-5xl max-h-[90vh]'
      : 'max-w-xl';
  const bodyClassName =
    size === 'large'
      ? 'max-h-[72vh] overflow-y-auto pr-1'
      : '';

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-900/50 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className={`w-full rounded-2xl bg-white p-5 shadow-soft dark:bg-slate-900 ${contentClassName}`}
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 16, opacity: 0 }}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">{title}</h3>
              <button className="btn-secondary !p-2" onClick={onClose}>
                <X size={16} />
              </button>
            </div>
            <div className={bodyClassName}>{children}</div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
