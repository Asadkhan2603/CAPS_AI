import { Bell, ChevronDown, History, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Pencil, Search, Sun, UserCircle2, UserRoundCog } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Breadcrumb from './Breadcrumb';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { unreadNoticeCount } from '../../utils/noticeReadTracker';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import { formatApiError } from '../../utils/apiError';

export default function Topbar({ user, onOpenMobile, collapsed, onToggleCollapse, isDark, onToggleTheme, onLogout }) {
  const [open, setOpen] = useState(false);
  const [noticeCount, setNoticeCount] = useState(0);
  const [logoVersion, setLogoVersion] = useState('');
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const logoInputRef = useRef(null);
  const { pushToast } = useToast();
  const isAdmin = user?.role === 'admin';
  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);
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
  }, [user?.id, user?.role]);

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

  async function onUploadLogo(file) {
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
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/88 px-3 py-2.5 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/88 sm:px-4 lg:px-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5 lg:gap-3">
          <button className="btn-secondary !p-2 lg:hidden" onClick={onOpenMobile}>
            <Menu size={16} />
          </button>
          <button className="btn-secondary !p-2 hidden lg:inline-flex" onClick={onToggleCollapse} title="Toggle Control Center">
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>

          <button
            type="button"
            className="relative flex min-w-0 items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-left shadow-sm transition hover:border-brand-200 dark:border-slate-800 dark:bg-slate-950/70 dark:hover:border-brand-800"
            onClick={() => {
              if (isAdmin && !uploadingLogo) {
                logoInputRef.current?.click();
              }
            }}
            title={isAdmin ? 'Click to update branding logo' : 'Branding'}
          >
            {isAdmin ? (
              <>
                <input
                  ref={logoInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.svg"
                  className="hidden"
                  onChange={(e) => onUploadLogo(e.target.files?.[0])}
                />
                <button
                  type="button"
                  className="absolute -right-2 -top-2 inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-brand-200 hover:text-brand-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                  onClick={(event) => {
                    event.stopPropagation();
                    logoInputRef.current?.click();
                  }}
                  title={uploadingLogo ? 'Uploading logo...' : 'Update header logo'}
                  disabled={uploadingLogo}
                >
                  <Pencil size={13} />
                </button>
              </>
            ) : null}
            {logoUrl ? (
              <img src={logoUrl} alt="Institute logo" className="h-10 w-10 rounded-xl object-contain" />
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-fuchsia-500 via-violet-500 to-brand-500 text-sm font-bold text-white">
                A
              </div>
            )}
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold tracking-tight text-slate-950 dark:text-white sm:text-xl">
                CAPS AI
              </p>
              <p className="truncate text-[11px] font-medium text-slate-500 dark:text-slate-400">
                {uploadingLogo ? 'Uploading branding logo...' : 'Academic Operations Dashboard'}
              </p>
            </div>
          </button>

          <div className="hidden min-w-0 lg:block">
            <Breadcrumb />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="relative hidden md:block">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input !h-9 !w-48 !rounded-2xl !border-slate-200 !bg-slate-50 !pl-8 !pr-3 !py-0 text-xs dark:!border-slate-700 dark:!bg-slate-900 lg:!w-56" placeholder="Quick search..." />
          </label>
          <Link to="/profile" className="btn-secondary !p-2 sm:hidden" title="Manage Profile">
            <UserRoundCog size={16} />
          </Link>
          <Link to="/history" className="btn-secondary !p-2" title="History">
            <History size={16} />
          </Link>
          <Link to="/communication/announcements" className="btn-secondary relative !p-2" title="Notices">
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
            <button className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-100/90 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700" onClick={() => setOpen((prev) => !prev)}>
              {avatarSrc ? (
                <img src={avatarSrc} alt="Profile" className="h-5 w-5 rounded-full object-cover" />
              ) : (
                <UserCircle2 size={16} />
              )}
              <span className="max-w-36 truncate">{user?.full_name}</span>
              <ChevronDown size={14} />
            </button>

            {open ? (
              <div className="absolute right-0 top-11 w-64 rounded-3xl border border-slate-200 bg-white p-3 shadow-soft dark:border-slate-700 dark:bg-slate-900">
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
