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
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(1200px_500px_at_15%_-10%,rgba(14,165,233,0.18),transparent),radial-gradient(900px_500px_at_90%_0%,rgba(99,102,241,0.18),transparent)] dark:bg-[radial-gradient(1200px_500px_at_15%_-10%,rgba(14,165,233,0.15),transparent),radial-gradient(900px_500px_at_90%_0%,rgba(99,102,241,0.14),transparent)]">
      <div className="relative z-10 flex min-h-screen">
        <Sidebar
          user={user}
          collapsed={collapsed}
          mobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
          onLogout={logout}
        />

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
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
            <div className="mx-auto w-full max-w-[1600px]">
              <Outlet />
            </div>
          </motion.main>
        </div>
      </div>

      <Toast toasts={toasts} onDismiss={removeToast} />
      {mobileOpen ? <button className="fixed inset-0 z-40 bg-black/35 lg:hidden" onClick={() => setMobileOpen(false)} /> : null}
    </div>
  );
}
