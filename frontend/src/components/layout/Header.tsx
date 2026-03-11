import {
  Bell,
  ChevronDown,
  History,
  LogOut,
  Menu,
  Moon,
  Pencil,
  Search,
  Sun,
  UserCircle2,
  UserRoundCog
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { unreadNoticeCount } from '../../utils/noticeReadTracker';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import { formatApiError } from '../../utils/apiError';
import { cn } from '../../utils/cn';

type HeaderProps = {
  user: any;
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenMobile: () => void;
  onLogout: () => void;
  headerHeight: number;
};

export default function Header({
  user,
  isDark,
  onToggleTheme,
  onOpenMobile,
  onLogout,
  headerHeight
}: HeaderProps) {
  const [openMenu, setOpenMenu] = useState(false);
  const [noticeCount, setNoticeCount] = useState(0);
  const [logoVersion, setLogoVersion] = useState('');
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const logoInputRef = useRef<HTMLInputElement | null>(null);
  const isAdmin = user?.role === 'admin';
  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);
  const { pushToast } = useToast() as {
    pushToast: (payload: { title: string; description: string; variant?: string }) => void;
  };

  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);
  const logoUrl = logoVersion
    ? `${backendBaseUrl}/api/v1/branding/logo?v=${encodeURIComponent(logoVersion)}`
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
  }, [user?.id]);

  useEffect(() => {
    let alive = true;
    async function loadLogoMeta() {
      try {
        const response = await apiClient.get('/branding/logo/meta');
        if (!alive) return;
        setLogoVersion(response.data?.has_logo ? String(response.data.updated_at || Date.now()) : '');
      } catch {
        if (!alive) return;
        setLogoVersion('');
      }
    }
    loadLogoMeta();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    function onWindowClick(event: MouseEvent) {
      if (!menuRef.current) {
        return;
      }
      const target = event.target as Node;
      if (!menuRef.current.contains(target)) {
        setOpenMenu(false);
      }
    }
    window.addEventListener('click', onWindowClick);
    return () => window.removeEventListener('click', onWindowClick);
  }, []);

  async function onUploadLogo(file?: File | null) {
    if (!file || !isAdmin) {
      return;
    }
    const suffix = `.${String(file.name || '').split('.').pop()?.toLowerCase() || ''}`;
    if (!['.png', '.jpg', '.jpeg', '.webp', '.svg'].includes(suffix)) {
      pushToast({
        title: 'Unsupported file',
        description: 'Use png, jpg, jpeg, webp, or svg for the branding logo.',
        variant: 'error'
      });
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      pushToast({
        title: 'File too large',
        description: 'Branding logo must be 2MB or smaller.',
        variant: 'error'
      });
      return;
    }
    try {
      setUploadingLogo(true);
      const multipart = new FormData();
      multipart.append('file', file);
      const response = await apiClient.post('/branding/logo', multipart);
      setLogoVersion(String(response.data?.updated_at || Date.now()));
      pushToast({
        title: 'Logo updated',
        description: 'Header branding logo updated successfully.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Upload failed',
        description: formatApiError(err, 'Failed to update branding logo'),
        variant: 'error'
      });
    } finally {
      setUploadingLogo(false);
      if (logoInputRef.current) {
        logoInputRef.current.value = '';
      }
    }
  }

  return (
    <header
      className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-white/92 shadow-sm backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/90"
      style={{ height: headerHeight }}
    >
      <div className="flex h-full items-center justify-between px-3 sm:px-4 lg:px-5">
        <div className="flex min-w-0 items-center gap-2.5">
          <button
            type="button"
            className="btn-secondary !p-2 lg:hidden"
            onClick={onOpenMobile}
            aria-label="Open navigation"
          >
            <Menu size={16} />
          </button>

          <button
            type="button"
            className="group relative flex min-w-0 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-2.5 py-2 transition hover:border-brand-200 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-brand-700"
            onClick={() => (isAdmin && !uploadingLogo ? logoInputRef.current?.click() : null)}
            title={isAdmin ? 'Update branding logo' : 'Branding'}
          >
            {isAdmin ? (
              <>
                <input
                  ref={logoInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.svg"
                  className="hidden"
                  onChange={(event) => onUploadLogo(event.target.files?.[0])}
                />
                <span className="absolute -right-1 -top-1 inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition group-hover:text-brand-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                  <Pencil size={12} />
                </span>
              </>
            ) : null}
            {logoUrl ? (
              <img src={logoUrl} alt="Brand logo" className="h-9 w-9 rounded-lg object-contain" />
            ) : (
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-fuchsia-500 via-violet-500 to-brand-500 text-sm font-bold text-white">
                A
              </div>
            )}
            <div className="min-w-0 text-left">
              <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">CAPS AI</p>
              <p className="truncate text-[11px] text-slate-500 dark:text-slate-400">
                {uploadingLogo ? 'Uploading logo...' : 'Academic Operations Dashboard'}
              </p>
            </div>
          </button>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          <label className="relative hidden md:block">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              className="input !h-9 !w-44 !rounded-2xl !border-slate-200 !bg-slate-50 !pl-8 !pr-3 !py-0 text-xs dark:!border-slate-700 dark:!bg-slate-900 lg:!w-56"
              placeholder="Quick search..."
            />
          </label>

          <Link to="/history" className="btn-secondary !p-2" title="History">
            <History size={16} />
          </Link>
          <Link to="/communication/announcements" className="btn-secondary relative !p-2" title="Notifications">
            <Bell size={16} />
            {noticeCount > 0 ? (
              <span className="absolute -right-1 -top-1 inline-flex min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-semibold text-white">
                {noticeCount > 9 ? '9+' : noticeCount}
              </span>
            ) : null}
          </Link>
          <button type="button" className="btn-secondary !p-2" onClick={onToggleTheme} title="Toggle theme">
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setOpenMenu((prev) => !prev)}
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-100/90 px-2.5 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
            >
              {avatarSrc ? (
                <img src={avatarSrc} alt="Profile" className="h-6 w-6 rounded-full object-cover" />
              ) : (
                <UserCircle2 size={16} />
              )}
              <span className="hidden max-w-36 truncate sm:inline">{user?.full_name || 'User'}</span>
              <ChevronDown size={14} className={cn('transition-transform', openMenu ? 'rotate-180' : 'rotate-0')} />
            </button>

            {openMenu ? (
              <div className="absolute right-0 top-11 w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-soft dark:border-slate-700 dark:bg-slate-900">
                <p className="text-sm font-semibold text-slate-900 dark:text-white">{user?.full_name || 'User'}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{user?.email}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Role: {user?.role}</p>
                <Link
                  className="btn-secondary mt-3 w-full justify-start"
                  to="/profile"
                  onClick={() => setOpenMenu(false)}
                >
                  <UserRoundCog size={15} /> Manage Profile
                </Link>
                <button className="btn-secondary mt-2 w-full justify-start" onClick={onLogout}>
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
