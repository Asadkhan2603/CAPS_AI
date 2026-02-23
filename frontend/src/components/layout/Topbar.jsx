import { Menu, Moon, Sun, UserCircle2, ChevronDown, LogOut, History, PanelLeftClose, PanelLeftOpen, UserRoundCog, Search, Bell } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Breadcrumb from './Breadcrumb';
import { apiClient } from '../../services/apiClient';
import { unreadNoticeCount } from '../../utils/noticeReadTracker';

export default function Topbar({ user, onOpenMobile, collapsed, onToggleCollapse, isDark, onToggleTheme, onLogout }) {
  const [open, setOpen] = useState(false);
  const [noticeCount, setNoticeCount] = useState(0);
  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);
  const avatarSrc = user?.avatar_url
    ? `${backendBaseUrl}${user.avatar_url}${user.avatar_updated_at ? `?v=${encodeURIComponent(user.avatar_updated_at)}` : ''}`
    : '';

  useEffect(() => {
    let alive = true;
    async function loadNoticeCount() {
      try {
        const resp = await apiClient.get('/notices/', { params: { include_expired: false, limit: 100 } });
        if (!alive) return;
        setNoticeCount(unreadNoticeCount(user?.id, resp.data || []));
      } catch {
        if (!alive) return;
        setNoticeCount(0);
      }
    }
    loadNoticeCount();
    const timer = setInterval(loadNoticeCount, 30000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [user?.id, user?.role]);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/80">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <button className="btn-secondary !p-2 lg:hidden" onClick={onOpenMobile}>
            <Menu size={16} />
          </button>
          <button className="btn-secondary !p-2 hidden lg:inline-flex" onClick={onToggleCollapse} title="Toggle Control Center">
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
          <div className="min-w-0">
            <Breadcrumb />
            <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-200">Academic Operations Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="relative hidden md:block">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input !h-9 !w-56 !rounded-xl !pl-8 !pr-3 !py-0 text-xs" placeholder="Quick search..." />
          </label>
          <Link to="/profile" className="btn-secondary !p-2 sm:hidden" title="Manage Profile">
            <UserRoundCog size={16} />
          </Link>
          <Link to="/history" className="btn-secondary !p-2" title="History">
            <History size={16} />
          </Link>
          <Link to="/communication/announcements" className="btn-secondary !p-2 relative" title="Notices">
            <Bell size={16} />
            {noticeCount > 0 ? (
              <span className="absolute -right-1 -top-1 inline-flex min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-semibold text-white">
                {noticeCount > 9 ? '9+' : noticeCount}
              </span>
            ) : null}
          </Link>
          <button className="btn-secondary !p-2" onClick={onToggleTheme}>
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          <div className="relative hidden sm:block">
            <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-100/90 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700" onClick={() => setOpen((prev) => !prev)}>
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
