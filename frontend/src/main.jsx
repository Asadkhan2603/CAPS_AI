import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import './styles/global.css';

const DYNAMIC_IMPORT_RELOAD_KEY = 'caps_ai_dynamic_import_reload_once';

function shouldReloadForDynamicImportFailure(error) {
  const message = String(error?.message || error || '').toLowerCase();
  return (
    message.includes('failed to fetch dynamically imported module') ||
    message.includes('error loading dynamically imported module') ||
    message.includes('importing a module script failed')
  );
}

function reloadOnceAfterDynamicImportFailure() {
  try {
    const didReload = sessionStorage.getItem(DYNAMIC_IMPORT_RELOAD_KEY) === '1';
    if (!didReload) {
      sessionStorage.setItem(DYNAMIC_IMPORT_RELOAD_KEY, '1');
      window.location.reload();
    }
  } catch {
    window.location.reload();
  }
}

window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault();
  reloadOnceAfterDynamicImportFailure();
});

window.addEventListener('unhandledrejection', (event) => {
  if (shouldReloadForDynamicImportFailure(event.reason)) {
    reloadOnceAfterDynamicImportFailure();
  }
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
