import { Outlet, useLocation } from 'react-router-dom';
import AppLayout from './AppLayout';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { useToast } from '../../hooks/useToast';

export default function DashboardLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { toasts, removeToast } = useToast();

  return (
    <AppLayout
      user={user}
      isDark={isDark}
      onToggleTheme={toggleTheme}
      onLogout={logout}
      toasts={toasts}
      onDismissToast={removeToast}
      locationKey={location.pathname}
    >
      <Outlet />
    </AppLayout>
  );
}
