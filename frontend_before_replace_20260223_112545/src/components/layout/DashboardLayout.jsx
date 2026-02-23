import { motion } from 'framer-motion';
import { Outlet, useLocation } from 'react-router-dom';
import { useState } from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import Toast from '../ui/Toast';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { useToast } from '../../hooks/useToast';

export default function DashboardLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { toasts, removeToast } = useToast();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-slate-100 to-brand-50 dark:from-slate-950 dark:via-slate-950 dark:to-slate-900">
      <div className="flex min-h-screen">
        <Sidebar
          user={user}
          collapsed={collapsed}
          mobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
          onLogout={logout}
        />

        <div className="flex min-h-screen flex-1 flex-col">
          <Topbar
            user={user}
            onOpenMobile={() => setMobileOpen(true)}
            collapsed={collapsed}
            onToggleCollapse={() => setCollapsed((prev) => !prev)}
            isDark={isDark}
            onToggleTheme={toggleTheme}
            onLogout={logout}
          />
          <motion.main
            key={location.pathname}
            className="flex-1 px-4 py-5 lg:px-6"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
          >
            <Outlet />
          </motion.main>
        </div>
      </div>

      <Toast toasts={toasts} onDismiss={removeToast} />
      {mobileOpen ? <button className="fixed inset-0 z-40 bg-black/35 lg:hidden" onClick={() => setMobileOpen(false)} /> : null}
    </div>
  );
}
