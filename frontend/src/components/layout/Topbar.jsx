import { Menu, Moon, Sun, UserCircle2, ChevronDown, LogOut, History, PanelLeftClose, PanelLeftOpen, UserRoundCog } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Breadcrumb from './Breadcrumb';
import { apiClient } from '../../services/apiClient';

export default function Topbar({ user, onOpenMobile, collapsed, onToggleCollapse, isDark, onToggleTheme, onLogout }) {
  const [open, setOpen] = useState(false);
  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);
  const avatarSrc = user?.avatar_url
    ? `${backendBaseUrl}${user.avatar_url}${user.avatar_updated_at ? `?v=${encodeURIComponent(user.avatar_updated_at)}` : ''}`
    : '';

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/85 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button className="btn-secondary !p-2 lg:hidden" onClick={onOpenMobile}>
            <Menu size={16} />
          </button>
          <button className="btn-secondary !p-2 hidden lg:inline-flex" onClick={onToggleCollapse} title="Toggle Control Center">
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
          <div>
            <Breadcrumb />
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Academic Operations Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/profile" className="btn-secondary !p-2 sm:hidden" title="Manage Profile">
            <UserRoundCog size={16} />
          </Link>
          <Link to="/history" className="btn-secondary !p-2" title="History">
            <History size={16} />
          </Link>
          <button className="btn-secondary !p-2" onClick={onToggleTheme}>
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          <div className="relative hidden sm:block">
            <button className="btn-secondary" onClick={() => setOpen((prev) => !prev)}>
              {avatarSrc ? (
                <img src={avatarSrc} alt="Profile" className="h-5 w-5 rounded-full object-cover" />
              ) : (
                <UserCircle2 size={16} />
              )}
              <span>{user?.full_name}</span>
              <ChevronDown size={14} />
            </button>

            {open ? (
              <div className="absolute right-0 top-11 w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-soft dark:border-slate-700 dark:bg-slate-900">
                <p className="text-sm font-semibold">{user?.full_name}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
                <p className="mt-1 text-xs text-slate-500">Role: {user?.role}</p>
                <Link className="btn-secondary mt-3 w-full justify-start" to="/profile" onClick={() => setOpen(false)}>
                  <UserRoundCog size={15} /> Manage Profile
                </Link>
                <button className="btn-secondary mt-3 w-full justify-start" onClick={onLogout}>
                  <LogOut size={15} /> Logout
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
