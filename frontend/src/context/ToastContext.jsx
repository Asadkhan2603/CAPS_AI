import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const pushToast = useCallback(
    (payload) => {
      const id = crypto.randomUUID();
      const toast = {
        id,
        title: payload.title || 'Notice',
        description: payload.description || '',
        variant: payload.variant || 'info'
      };
      setToasts((prev) => [toast, ...prev]);
      setTimeout(() => removeToast(id), payload.duration ?? 3200);
    },
    [removeToast]
  );

  const value = useMemo(() => ({ toasts, pushToast, removeToast }), [toasts, pushToast, removeToast]);

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToastContext() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToastContext must be used inside ToastProvider');
  }
  return context;
}
