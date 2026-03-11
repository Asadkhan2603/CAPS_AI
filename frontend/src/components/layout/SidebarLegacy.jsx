import {
  Bell,
  ClipboardCheck,
  ChevronDown,
  ChevronRight,
  FileText,
  GraduationCap,
  House,
  LogOut,
  Megaphone,
  Pencil,
  School,
  Shield,
  UserCircle2,
  Users,
  Wrench
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { getVisibleNavigationGroups, getWorkspaceItemPath } from '../../config/navigationGroups';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import { formatApiError } from '../../utils/apiError';

const groupIconMap = {
  adminPanel: Shield,
  overview: House,
  home: House,
  academics: GraduationCap,
  assignments: FileText,
  results: FileText,
  attendance: ClipboardCheck,
  notices: Bell,
  communication: Megaphone,
  clubs: Users,
  operations: Wrench,
  setup: School,
  profile: UserCircle2
};

function titleize(value) {
  if (!value) {
    return '';
  }
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function getEnrollmentLabel(user) {
  const explicit = user?.profile?.enrollment_number;
  if (explicit) {
    return explicit;
  }
  const email = user?.email || '';
  if (email.includes('@')) {
    return email.split('@')[0];
  }
  return '';
}

function getUserMeta(user) {
  const profile = user?.profile || {};
  if (user?.role === 'student') {
    return [
      profile.department || '',
      profile.branch || profile.branch_name || '',
      getEnrollmentLabel(user)
    ].filter(Boolean);
  }
  if (user?.role === 'teacher') {
    return [
      profile.designation || 'Faculty Member',
      profile.department || ''
    ].filter(Boolean);
  }
  if (user?.role === 'admin') {
    return [
      titleize(user?.admin_type || 'admin'),
      profile.department || profile.designation || ''
    ].filter(Boolean);
  }
  return [profile.department || profile.designation || ''].filter(Boolean);
}

export default function Sidebar({ user, collapsed, mobileOpen, onCloseMobile, onLogout }) {
  const location = useLocation();
  const role = user?.role;
  const isAdmin = role === 'admin';
  const { pushToast } = useToast();
  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);
  const [activeGroupKey, setActiveGroupKey] = useState('');
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const logoInputRef = useRef(null);
  const visibleGroups = useMemo(
    () => getVisibleNavigationGroups(user),
    [user]
  );
  const userMeta = useMemo(() => getUserMeta(user), [user]);
  const roleLabel = useMemo(() => {
    if (role === 'admin') {
      return titleize(user?.admin_type || 'admin');
    }
    return titleize(role || 'member');
  }, [role, user?.admin_type]);

  useEffect(() => {
    const hubGroupKey = location.pathname.startsWith('/workspace/')
      ? location.pathname.split('/')[2] || ''
      : '';
    const routeMatchedGroup =
      visibleGroups.find((group) => group.key === hubGroupKey) ||
      visibleGroups.find((group) => group.items.some((item) => location.pathname.startsWith(item.to)));
    if (routeMatchedGroup) {
      setActiveGroupKey(routeMatchedGroup.key);
      return;
    }
    setActiveGroupKey((prev) => (
      visibleGroups.some((group) => group.key === prev) ? prev : (visibleGroups[0]?.key || '')
    ));
  }, [location.pathname, visibleGroups]);

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
      await apiClient.post('/branding/logo', multipart);
      pushToast({
        title: 'Logo updated',
        description: 'Branding logo updated successfully.',
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

  function isRouteActive(pathname) {
    return location.pathname === pathname || location.pathname.startsWith(`${pathname}/`);
  }

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white/95 px-4 py-5 transition-transform duration-300 dark:border-slate-800 dark:bg-slate-900/95 lg:static lg:translate-x-0',
        collapsed ? 'lg:w-24' : 'lg:w-72',
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      <div className={cn('mb-5 space-y-4', collapsed && 'lg:items-center')}>
        <div className={cn('overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950/40', collapsed ? 'lg:hidden' : '')}>
          <div className="relative px-4 pb-4 pt-3.5">
            <Link
              to="/profile"
              onClick={onCloseMobile}
              className="absolute right-3.5 top-3.5 inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-500 transition hover:border-brand-200 hover:text-brand-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              title="Manage profile"
            >
              <Pencil size={14} />
            </Link>

            <div className="flex flex-col items-center text-center">
              {avatarSrc ? (
                <img
                  src={avatarSrc}
                  alt="Profile"
                  className="h-16 w-16 rounded-[1.2rem] border border-slate-200 object-cover shadow-sm dark:border-slate-700"
                />
              ) : (
                <div className="flex h-16 w-16 items-center justify-center rounded-[1.2rem] border border-dashed border-slate-300 bg-slate-50 text-slate-400 dark:border-slate-700 dark:bg-slate-900">
                  <UserCircle2 size={26} />
                </div>
              )}

              <p className="mt-3 text-lg font-semibold leading-tight text-slate-950 dark:text-white">
                {user?.full_name || 'User'}
              </p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-300">{roleLabel}</p>

              {userMeta.length > 0 ? (
                <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5">
                  {userMeta.slice(0, 3).map((item) => (
                    <span
                      key={item}
                      className="rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-medium text-brand-700 dark:bg-brand-900/40 dark:text-brand-200"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              ) : null}

              {isAdmin ? (
                <div className="mt-4 w-full border-t border-slate-200 pt-3 dark:border-slate-800">
                  <input
                    ref={logoInputRef}
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp,.svg"
                    className="hidden"
                    onChange={(e) => onUploadLogo(e.target.files?.[0])}
                  />
                  <button
                    type="button"
                    className="btn-secondary w-full justify-center !py-1.5 text-xs"
                    onClick={() => logoInputRef.current?.click()}
                    disabled={uploadingLogo}
                  >
                    {uploadingLogo ? 'Uploading logo...' : 'Update Brand Logo'}
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {collapsed ? (
          <div className="hidden lg:flex lg:justify-center">
            {avatarSrc ? (
              <img src={avatarSrc} alt="Profile" className="h-11 w-11 rounded-2xl border border-slate-200 object-cover dark:border-slate-700" />
            ) : (
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                <UserCircle2 size={18} />
              </div>
            )}
          </div>
        ) : null}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto pr-1">
        {collapsed ? (
          visibleGroups.map((group) => {
            const GroupIcon = groupIconMap[group.key] || group.items[0]?.icon || House;
            const groupLandingPath = getWorkspaceItemPath(group.key, group.items[0].to);
            const groupActive = group.items.some((item) => isRouteActive(getWorkspaceItemPath(group.key, item.to)));

            return (
              <Link
                key={group.key}
                to={groupLandingPath}
                onClick={onCloseMobile}
                title={`${group.label} (${group.items.length} modules)`}
                aria-label={group.label}
                className={cn(
                  'flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition',
                  groupActive
                    ? 'bg-gradient-to-r from-brand-100 to-indigo-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
                  'justify-center px-2'
                )}
              >
                {GroupIcon ? <GroupIcon size={16} /> : null}
              </Link>
            );
          })
        ) : (
          <div className="space-y-3">
            {visibleGroups.map((group) => {
              const isOpen = activeGroupKey === group.key;
              const GroupIcon = groupIconMap[group.key] || group.items[0]?.icon || House;
              const singleItem = group.items.length === 1 ? group.items[0] : null;
              const singleItemPath = singleItem ? getWorkspaceItemPath(group.key, singleItem.to) : '';
              const groupActive = group.items.some((item) => isRouteActive(getWorkspaceItemPath(group.key, item.to)));

              if (singleItem) {
                return (
                  <div key={group.key} className="border-t border-slate-200 pt-3 first:border-t-0 first:pt-0 dark:border-slate-800">
                    <NavLink
                      to={singleItemPath}
                      onClick={onCloseMobile}
                      className={() =>
                        cn(
                          'flex items-center gap-3 rounded-2xl px-4 py-3 transition',
                          groupActive
                            ? 'bg-gradient-to-r from-brand-50 to-indigo-50 text-brand-700 shadow-sm ring-1 ring-brand-100 dark:from-brand-900/30 dark:to-slate-900 dark:text-brand-200 dark:ring-brand-900/50'
                            : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-900'
                        )
                      }
                    >
                      <span
                        className={cn(
                          'inline-flex h-10 w-10 items-center justify-center rounded-xl border',
                          groupActive
                            ? 'border-brand-200 bg-white text-brand-600 dark:border-brand-800 dark:bg-slate-950 dark:text-brand-200'
                            : 'border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
                        )}
                      >
                        {GroupIcon ? <GroupIcon size={18} /> : null}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-base font-semibold">{group.label}</p>
                        <p className="truncate text-xs text-slate-500 dark:text-slate-400">{singleItem.label}</p>
                      </div>
                    </NavLink>
                  </div>
                );
              }

              return (
                <div key={group.key} className="border-t border-slate-200 pt-3 first:border-t-0 first:pt-0 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setActiveGroupKey((prev) => (prev === group.key ? '' : group.key))}
                    className={cn(
                      'flex min-h-12 w-full items-center justify-between rounded-2xl px-4 py-3 text-left transition',
                      groupActive
                        ? 'bg-gradient-to-r from-brand-50 to-indigo-50 text-brand-700 shadow-sm ring-1 ring-brand-100 dark:from-brand-900/30 dark:to-slate-900 dark:text-brand-200 dark:ring-brand-900/50'
                        : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-900'
                    )}
                  >
                    <span className="flex min-w-0 items-center gap-3">
                      <span
                        className={cn(
                          'inline-flex h-10 w-10 items-center justify-center rounded-xl border',
                          groupActive
                            ? 'border-brand-200 bg-white text-brand-600 dark:border-brand-800 dark:bg-slate-950 dark:text-brand-200'
                            : 'border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
                        )}
                      >
                        {GroupIcon ? <GroupIcon size={18} /> : null}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-base font-semibold">{group.label}</span>
                        <span className="block text-xs text-slate-500 dark:text-slate-400">
                          {group.items.length} modules
                        </span>
                      </span>
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="rounded-full bg-white/80 px-2 py-1 text-[11px] font-semibold text-slate-500 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700">
                        {group.items.length}
                      </span>
                      {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </span>
                  </button>

                  {isOpen ? (
                    <div className="ml-5 mt-2 space-y-1 border-l border-slate-200 pl-5 dark:border-slate-800">
                      {group.items.map((item) => {
                        const resolvedTo = getWorkspaceItemPath(group.key, item.to);
                        return (
                          <NavLink
                            key={resolvedTo}
                            to={resolvedTo}
                            onClick={onCloseMobile}
                            className={({ isActive }) =>
                              cn(
                                'flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition',
                                isActive
                                  ? 'bg-slate-100 text-brand-700 dark:bg-slate-900 dark:text-brand-200'
                                  : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900'
                              )
                            }
                          >
                            {item.icon ? <item.icon size={16} /> : null}
                            <span className="font-medium">{item.label}</span>
                          </NavLink>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </nav>

      <button className="btn-secondary mt-4 justify-start rounded-2xl" onClick={onLogout}>
        <LogOut size={16} /> Logout
      </button>
    </aside>
  );
}
