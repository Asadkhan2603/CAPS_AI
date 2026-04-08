import {
  Bell,
  ChevronDown,
  Ellipsis,
  History,
  LogOut,
  Menu,
  Moon,
  PanelLeft,
  Pencil,
  Search,
  Star,
  Sun,
  UserCircle2,
  UserRoundCog,
  X
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import { getVisibleNavigationGroups, getWorkspaceItemPath } from '../../config/navigationGroups';
import { formatApiError } from '../../utils/apiError';
import { cn } from '../../utils/cn';
import { buildQuickSearchItems, findQuickSearchMatches } from '../../utils/quickSearch';
import {
  type NavigationShortcutItem,
  readStoredShortcutPaths,
  recordRecentShortcut,
  resolveShortcutItems,
  toggleFavoriteShortcut,
  writeStoredShortcutPaths
} from '../../utils/navigationShortcuts';

type HeaderProps = {
  user: any;
  initialNotificationCount?: number;
  initialLogoVersion?: string;
  isDark: boolean;
  onToggleTheme: () => void;
  onToggleMobileNavigation: (trigger?: HTMLElement | null) => void;
  isMobileNavigationOpen: boolean;
  onToggleDesktopSidebar: () => void;
  isDesktopSidebarExpanded: boolean;
  onLogout: () => void;
  headerHeight: number;
};

type QuickSearchItem = NavigationShortcutItem & {
  id: string;
  keywords: string;
};

function getFocusableElements(container: HTMLElement | null) {
  if (!container) {
    return [];
  }
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hasAttribute('disabled') && element.getAttribute('aria-hidden') !== 'true');
}

function trapFocusWithinContainer(event: ReactKeyboardEvent<HTMLElement>, container: HTMLElement | null) {
  if (event.key !== 'Tab') {
    return;
  }
  const focusableElements = getFocusableElements(container);
  if (!focusableElements.length) {
    event.preventDefault();
    return;
  }
  const first = focusableElements[0];
  const last = focusableElements[focusableElements.length - 1];
  const activeElement = document.activeElement;

  if (event.shiftKey && activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

export default function Header({
  user,
  initialNotificationCount,
  initialLogoVersion = '',
  isDark,
  onToggleTheme,
  onToggleMobileNavigation,
  isMobileNavigationOpen,
  onToggleDesktopSidebar,
  isDesktopSidebarExpanded,
  onLogout,
  headerHeight
}: HeaderProps) {
  const [openMenu, setOpenMenu] = useState(false);
  const [openUtilities, setOpenUtilities] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearchIndex, setActiveSearchIndex] = useState(0);
  const [notificationCount, setNotificationCount] = useState(
    typeof initialNotificationCount === 'number' ? initialNotificationCount : 0
  );
  const [logoVersion, setLogoVersion] = useState(initialLogoVersion);
  const [showLogoImage, setShowLogoImage] = useState(true);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [favoritePaths, setFavoritePaths] = useState<string[]>([]);
  const [recentPaths, setRecentPaths] = useState<string[]>([]);
  const [shortcutsReady, setShortcutsReady] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const menuTriggerRef = useRef<HTMLButtonElement | null>(null);
  const menuPanelRef = useRef<HTMLDivElement | null>(null);
  const loadedShortcutOwnerRef = useRef('');
  const utilitiesRef = useRef<HTMLDivElement | null>(null);
  const utilitiesTriggerRef = useRef<HTMLButtonElement | null>(null);
  const utilitiesPanelRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const searchPanelRef = useRef<HTMLDivElement | null>(null);
  const searchTriggerRef = useRef<HTMLElement | null>(null);
  const logoInputRef = useRef<HTMLInputElement | null>(null);
  const isAdmin = user?.role === 'admin';
  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);
  const navigate = useNavigate();
  const location = useLocation();
  const { pushToast } = useToast() as {
    pushToast: (payload: { title: string; description: string; variant?: string }) => void;
  };
  const quickSearchItems = useMemo<QuickSearchItem[]>(
    () => buildQuickSearchItems(getVisibleNavigationGroups(user), getWorkspaceItemPath),
    [user]
  );
  const quickSearchMatches = useMemo(
    () => findQuickSearchMatches(quickSearchItems, searchQuery, 8),
    [quickSearchItems, searchQuery]
  );
  const visibleSearchPaths = useMemo(
    () => quickSearchItems.map((item) => item.path),
    [quickSearchItems]
  );
  const shortcutStorageSuffix = useMemo(
    () => user?.id || `${user?.role || 'guest'}:${user?.admin_type || 'default'}`,
    [user?.admin_type, user?.id, user?.role]
  );
  const favoriteStorageKey = `caps.navigation.favorite.${shortcutStorageSuffix}`;
  const recentStorageKey = `caps.navigation.recent.${shortcutStorageSuffix}`;
  const { favorites: favoriteShortcutItems, recent: recentShortcutItems } = useMemo(
    () => resolveShortcutItems(quickSearchItems, favoritePaths, recentPaths),
    [favoritePaths, quickSearchItems, recentPaths]
  );
  const iconButtonClass =
    'btn-secondary h-9 w-9 shrink-0 border border-slate-200/80 bg-white/78 text-slate-500 shadow-sm shadow-slate-200/40 !p-0 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-700 dark:border-slate-800 dark:bg-slate-900/72 dark:text-slate-300 dark:shadow-none dark:hover:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-white';
  const primaryNavButtonClass =
    'h-9 w-9 shrink-0 rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50 via-sky-50 to-white text-brand-700 shadow-sm shadow-brand-200/60 transition hover:border-brand-300 hover:from-brand-100 hover:via-sky-100 hover:to-white dark:border-brand-700/70 dark:from-brand-900/40 dark:via-slate-900 dark:to-slate-950 dark:text-brand-200';
  const inlineDesktopToggleClass =
    'hidden h-9 shrink-0 items-center gap-2 rounded-2xl border border-brand-200 bg-gradient-to-r from-brand-50 to-white px-3 text-sm font-semibold text-brand-700 shadow-sm shadow-brand-200/40 transition hover:border-brand-300 hover:from-brand-100 hover:to-white dark:border-brand-700/70 dark:from-brand-900/30 dark:to-slate-950 dark:text-brand-200 lg:inline-flex';
  const desktopSearchClass =
    'hidden h-9 shrink-0 md:inline-flex md:min-w-[12rem] md:items-center md:justify-between md:gap-3 md:rounded-2xl md:border md:border-slate-200/80 md:bg-slate-50/90 md:px-3 md:text-xs md:text-slate-500 md:shadow-sm md:shadow-slate-200/30 dark:md:border-slate-800 dark:md:bg-slate-900/75 dark:md:text-slate-400 dark:md:shadow-none lg:min-w-[15rem]';
  const profileTriggerClass =
    'inline-flex h-9 shrink-0 items-center gap-2 rounded-2xl border border-slate-200/85 bg-slate-100/92 px-2.5 text-sm font-semibold text-slate-700 shadow-sm shadow-slate-200/30 transition hover:border-slate-300 hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800/92 dark:text-slate-100 dark:shadow-none dark:hover:border-slate-600 dark:hover:bg-slate-700';
  const isNotificationsActive = location.pathname.startsWith('/notifications');
  const notificationButtonClass = cn(
    iconButtonClass,
    isNotificationsActive
      ? 'border-brand-200 bg-brand-50 text-brand-700 shadow-brand-200/50 dark:border-brand-700/60 dark:bg-brand-900/30 dark:text-brand-200'
      : '',
    notificationCount > 0
      ? 'border-rose-200/90 bg-rose-50/80 text-rose-700 shadow-rose-200/50 dark:border-rose-800/80 dark:bg-rose-950/40 dark:text-rose-200'
      : ''
  );

  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);
  const logoUrl = `${backendBaseUrl}/api/v1/branding/logo${
    logoVersion ? `?v=${encodeURIComponent(logoVersion)}` : ''
  }`;

  useEffect(() => {
    setNotificationCount(typeof initialNotificationCount === 'number' ? initialNotificationCount : 0);
  }, [initialNotificationCount]);

  useEffect(() => {
    setLogoVersion(initialLogoVersion || '');
  }, [initialLogoVersion]);

  useEffect(() => {
    loadedShortcutOwnerRef.current = shortcutStorageSuffix;
    setFavoritePaths(readStoredShortcutPaths(favoriteStorageKey));
    setRecentPaths(readStoredShortcutPaths(recentStorageKey));
    setShortcutsReady(true);
  }, [favoriteStorageKey, recentStorageKey, shortcutStorageSuffix]);

  useEffect(() => {
    setFavoritePaths((prev) => prev.filter((path) => visibleSearchPaths.includes(path)));
    setRecentPaths((prev) => prev.filter((path) => visibleSearchPaths.includes(path)));
  }, [visibleSearchPaths]);

  useEffect(() => {
    if (!shortcutsReady || loadedShortcutOwnerRef.current !== shortcutStorageSuffix) {
      return;
    }
    writeStoredShortcutPaths(favoriteStorageKey, favoritePaths);
  }, [favoritePaths, favoriteStorageKey, shortcutStorageSuffix, shortcutsReady]);

  useEffect(() => {
    if (!shortcutsReady || loadedShortcutOwnerRef.current !== shortcutStorageSuffix) {
      return;
    }
    writeStoredShortcutPaths(recentStorageKey, recentPaths);
  }, [recentPaths, recentStorageKey, shortcutStorageSuffix, shortcutsReady]);

  useEffect(() => {
    if (!shortcutsReady || !visibleSearchPaths.length) {
      return;
    }
    setRecentPaths((prev) => recordRecentShortcut(prev, location.pathname, visibleSearchPaths, 5));
  }, [location.pathname, shortcutsReady, visibleSearchPaths]);

  useEffect(() => {
    let alive = true;
    async function loadNotificationCount() {
      try {
        const resp = await apiClient.get('/notifications/unread-count');
        if (!alive) return;
        setNotificationCount(Number(resp.data?.count || 0));
      } catch {
        if (!alive) return;
        setNotificationCount(0);
      }
    }
    const triggerNotificationCountRefresh = () => {
      void loadNotificationCount();
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void loadNotificationCount();
      }
    };
    const shouldSkipImmediateFetch = typeof initialNotificationCount === 'number';
    if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
      const idleId = shouldSkipImmediateFetch
        ? null
        : window.requestIdleCallback(() => {
            void loadNotificationCount();
          }, { timeout: 1500 });
      window.addEventListener('focus', triggerNotificationCountRefresh);
      window.addEventListener('caps-ai:notifications-changed', triggerNotificationCountRefresh as EventListener);
      document.addEventListener('visibilitychange', onVisibilityChange);
      const timer = setInterval(triggerNotificationCountRefresh, 60000);
      return () => {
        alive = false;
        if (idleId !== null) {
          window.cancelIdleCallback(idleId);
        }
        clearInterval(timer);
        window.removeEventListener('focus', triggerNotificationCountRefresh);
        window.removeEventListener('caps-ai:notifications-changed', triggerNotificationCountRefresh as EventListener);
        document.removeEventListener('visibilitychange', onVisibilityChange);
      };
    }
    if (!shouldSkipImmediateFetch) {
      void loadNotificationCount();
    }
    const timer = setInterval(triggerNotificationCountRefresh, 60000);
    window.addEventListener('focus', triggerNotificationCountRefresh);
    window.addEventListener('caps-ai:notifications-changed', triggerNotificationCountRefresh as EventListener);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      alive = false;
      clearInterval(timer);
      window.removeEventListener('focus', triggerNotificationCountRefresh);
      window.removeEventListener('caps-ai:notifications-changed', triggerNotificationCountRefresh as EventListener);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [user?.id, initialNotificationCount]);

  useEffect(() => {
    function onWindowClick(event: MouseEvent) {
      const target = event.target as Node;
      if (menuRef.current && !menuRef.current.contains(target)) {
        closeProfileMenu(false);
      }
      if (utilitiesRef.current && !utilitiesRef.current.contains(target)) {
        closeUtilitiesMenu(false);
      }
    }
    window.addEventListener('click', onWindowClick);
    return () => window.removeEventListener('click', onWindowClick);
  }, []);

  useEffect(() => {
    if (!isSearchOpen) {
      setSearchQuery('');
      setActiveSearchIndex(0);
      return;
    }
    const timer = window.setTimeout(() => {
      searchInputRef.current?.focus();
      searchInputRef.current?.select();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [isSearchOpen]);

  useEffect(() => {
    if (!openMenu) {
      return;
    }
    const timer = window.setTimeout(() => {
      const focusableElements = getFocusableElements(menuPanelRef.current);
      focusableElements[0]?.focus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [openMenu]);

  useEffect(() => {
    if (!openUtilities) {
      return;
    }
    const timer = window.setTimeout(() => {
      const focusableElements = getFocusableElements(utilitiesPanelRef.current);
      focusableElements[0]?.focus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [openUtilities]);

  useEffect(() => {
    setActiveSearchIndex(0);
  }, [searchQuery]);

  useEffect(() => {
    function onGlobalKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const isTypingTarget =
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.tagName === 'SELECT' ||
        target?.isContentEditable;

      if (event.key === 'Escape') {
        closeProfileMenu();
        closeUtilitiesMenu();
        closeSearch();
        return;
      }

      if (event.key === '/' && !event.metaKey && !event.ctrlKey && !event.altKey && !isTypingTarget) {
        event.preventDefault();
        searchTriggerRef.current = null;
        setIsSearchOpen(true);
      }
    }

    window.addEventListener('keydown', onGlobalKeyDown);
    return () => window.removeEventListener('keydown', onGlobalKeyDown);
  }, []);

  function openSearch(trigger?: HTMLElement | null) {
    searchTriggerRef.current = trigger || null;
    setIsSearchOpen(true);
  }

  function closeSearch(restoreFocus = true) {
    const wasOpen = isSearchOpen;
    setIsSearchOpen(false);
    if (restoreFocus && wasOpen && searchTriggerRef.current) {
      const timer = window.setTimeout(() => {
        searchTriggerRef.current?.focus();
      }, 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }

  function openSearchMatch(path?: string) {
    if (!path) {
      return;
    }
    navigate(path);
    closeSearch(false);
  }

  function toggleFavoritePath(path: string) {
    setFavoritePaths((prev) => toggleFavoriteShortcut(prev, path, visibleSearchPaths, 6));
  }

  function renderShortcutRows(items: NavigationShortcutItem[], includeFavoriteAction = false) {
    return (
      <div className="space-y-1">
        {items.map((item) => {
          const isFavorite = favoritePaths.includes(item.path);
          return (
            <div
              key={item.path}
              className="flex items-center gap-2 rounded-2xl bg-slate-50 p-1 text-slate-700 transition hover:bg-slate-100 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <button
                type="button"
                className="flex flex-1 items-center justify-between rounded-[1rem] px-3 py-2 text-left"
                onClick={() => openSearchMatch(item.path)}
              >
                <span>
                  <span className="block text-sm font-semibold">{item.label}</span>
                  <span className="block text-xs text-slate-500 dark:text-slate-400">{item.groupLabel}</span>
                </span>
                <span className="text-xs text-slate-400">{item.path}</span>
              </button>
              {includeFavoriteAction ? (
                <button
                  type="button"
                  className={cn(
                    'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition',
                    isFavorite
                      ? 'border-amber-200 bg-amber-50 text-amber-600 hover:bg-amber-100 dark:border-amber-700/60 dark:bg-amber-900/20 dark:text-amber-300 dark:hover:bg-amber-900/35'
                      : 'border-slate-200 bg-white text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-200'
                  )}
                  aria-label={isFavorite ? `Remove ${item.label} from favorites` : `Add ${item.label} to favorites`}
                  title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                  onClick={() => toggleFavoritePath(item.path)}
                >
                  <Star size={14} className={isFavorite ? 'fill-current' : ''} />
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
    );
  }

  function toggleProfileMenu() {
    if (openMenu) {
      closeProfileMenu();
      return;
    }
    setOpenMenu(true);
  }

  function toggleUtilitiesMenu() {
    if (openUtilities) {
      closeUtilitiesMenu();
      return;
    }
    setOpenUtilities(true);
  }

  function closeProfileMenu(restoreFocus = true) {
    const wasOpen = openMenu;
    setOpenMenu(false);
    if (restoreFocus && wasOpen) {
      const timer = window.setTimeout(() => {
        menuTriggerRef.current?.focus();
      }, 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }

  function closeUtilitiesMenu(restoreFocus = true) {
    const wasOpen = openUtilities;
    setOpenUtilities(false);
    if (restoreFocus && wasOpen) {
      const timer = window.setTimeout(() => {
        utilitiesTriggerRef.current?.focus();
      }, 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }

  function onSearchInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (!quickSearchMatches.length && event.key === 'Enter') {
      event.preventDefault();
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveSearchIndex((prev) => Math.min(prev + 1, quickSearchMatches.length - 1));
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSearchIndex((prev) => Math.max(prev - 1, 0));
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      openSearchMatch(quickSearchMatches[activeSearchIndex]?.path || quickSearchMatches[0]?.path);
    }
  }

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
      setShowLogoImage(true);
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
      <div className="flex h-full items-center justify-between px-2.5 sm:px-3 lg:px-5">
        <div className="flex min-w-0 items-center gap-2 sm:gap-2.5">
          <button
            type="button"
            className={cn(primaryNavButtonClass, 'lg:hidden')}
            onClick={(event) => onToggleMobileNavigation(event.currentTarget)}
            aria-label={isMobileNavigationOpen ? 'Close navigation' : 'Open navigation'}
            title={isMobileNavigationOpen ? 'Close navigation' : 'Open navigation'}
          >
            {isMobileNavigationOpen ? <X size={16} /> : <Menu size={16} />}
          </button>

          <button
            type="button"
            className="group relative flex min-w-0 max-w-[10.5rem] items-center gap-2 rounded-2xl border border-slate-200 bg-white px-2 py-1.5 transition hover:border-brand-200 sm:max-w-[13rem] sm:px-2.5 sm:py-2 lg:max-w-none dark:border-slate-700 dark:bg-slate-900 dark:hover:border-brand-700"
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
            {showLogoImage ? (
              <img
                src={logoUrl}
                alt="Brand logo"
                className="h-9 w-9 rounded-lg object-contain"
                onLoad={() => setShowLogoImage(true)}
                onError={() => setShowLogoImage(false)}
              />
            ) : (
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-fuchsia-500 via-violet-500 to-brand-500 text-sm font-bold text-white">
                A
              </div>
            )}
            <div className="min-w-0 text-left">
              <p className="truncate text-sm font-semibold text-slate-900 sm:hidden dark:text-white">CAPS</p>
              <p className="hidden truncate text-sm font-semibold text-slate-900 sm:block dark:text-white">CAPS AI</p>
              <p className="hidden truncate text-[11px] text-slate-500 lg:block dark:text-slate-400">
                {uploadingLogo ? 'Uploading logo...' : 'Academic Operations Dashboard'}
              </p>
            </div>
          </button>
        </div>

        <div className="flex items-center gap-1 sm:gap-1.5 lg:gap-2">
          <button
            type="button"
            className={inlineDesktopToggleClass}
            onClick={onToggleDesktopSidebar}
            title={isDesktopSidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-label={isDesktopSidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <PanelLeft size={16} />
          </button>

          <button
            type="button"
            className={desktopSearchClass}
            onClick={(event) => openSearch(event.currentTarget)}
            title="Open quick search"
            aria-label="Open quick search"
          >
            <span className="flex items-center gap-2">
              <Search size={14} />
              <span>Quick search...</span>
            </span>
            <span className="rounded-md border border-slate-200 px-1.5 py-0.5 text-[10px] dark:border-slate-700">
              /
            </span>
          </button>

          <button
            type="button"
            className={cn(iconButtonClass, 'md:hidden')}
            onClick={(event) => openSearch(event.currentTarget)}
            title="Search"
            aria-label="Search"
          >
            <Search size={16} />
          </button>

          <Link to="/history" className={cn(iconButtonClass, 'hidden lg:inline-flex')} title="History">
            <History size={16} />
          </Link>
          <Link to="/notifications" className={cn(notificationButtonClass, 'relative')} title="Notifications">
            <Bell size={16} />
            {notificationCount > 0 ? (
              <span className="absolute -right-1 -top-1 inline-flex min-w-[1.15rem] items-center justify-center rounded-full border border-white bg-rose-600 px-1 text-[10px] font-bold text-white shadow-sm shadow-rose-500/40 dark:border-slate-950">
                {notificationCount > 9 ? '9+' : notificationCount}
              </span>
            ) : null}
          </Link>
          <button
            type="button"
            className={cn(iconButtonClass, 'hidden lg:inline-flex')}
            onClick={onToggleTheme}
            title="Toggle theme"
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          <div className="relative lg:hidden" ref={utilitiesRef}>
            <button
              ref={utilitiesTriggerRef}
              type="button"
              className={iconButtonClass}
              onClick={toggleUtilitiesMenu}
              aria-haspopup="menu"
              aria-expanded={openUtilities}
              aria-controls="header-utilities-menu"
              title="More"
              aria-label="More actions"
            >
              <Ellipsis size={16} />
            </button>

            {openUtilities ? (
              <div
                id="header-utilities-menu"
                ref={utilitiesPanelRef}
                role="menu"
                aria-label="More actions"
                onKeyDown={(event) => trapFocusWithinContainer(event, utilitiesPanelRef.current)}
                className="absolute right-0 top-11 z-50 w-52 rounded-2xl border border-slate-200 bg-white p-2 shadow-soft dark:border-slate-700 dark:bg-slate-900"
              >
                <Link
                  className="btn-secondary w-full justify-start"
                  to="/history"
                  onClick={() => closeUtilitiesMenu(false)}
                >
                  <History size={15} /> History
                </Link>
                <Link
                  className="btn-secondary mt-2 w-full justify-start"
                  to="/help"
                  onClick={() => closeUtilitiesMenu(false)}
                >
                  <UserRoundCog size={15} /> Help & Support
                </Link>
                <button
                  type="button"
                  className="btn-secondary mt-2 w-full justify-start"
                  onClick={() => {
                    onToggleTheme();
                    closeUtilitiesMenu(false);
                  }}
                >
                  {isDark ? <Sun size={15} /> : <Moon size={15} />} {isDark ? 'Light mode' : 'Dark mode'}
                </button>
              </div>
            ) : null}
          </div>

          <div className="relative" ref={menuRef}>
            <button
              ref={menuTriggerRef}
              type="button"
              onClick={toggleProfileMenu}
              aria-haspopup="menu"
              aria-expanded={openMenu}
              aria-controls="header-profile-menu"
              className={profileTriggerClass}
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
              <div
                id="header-profile-menu"
                ref={menuPanelRef}
                role="menu"
                aria-label="Profile menu"
                onKeyDown={(event) => trapFocusWithinContainer(event, menuPanelRef.current)}
                className="absolute right-0 top-11 w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-soft dark:border-slate-700 dark:bg-slate-900"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">{user?.full_name || 'User'}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{user?.email}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Role: {user?.role}</p>
                  </div>
                  <button type="button" className={iconButtonClass} onClick={() => closeProfileMenu()}>
                    <X size={14} />
                  </button>
                </div>
                <Link
                  className="btn-secondary mt-3 w-full justify-start"
                  to="/profile"
                  onClick={() => closeProfileMenu(false)}
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

      {isSearchOpen ? (
        <div className="fixed inset-0 z-[60] bg-slate-950/45 p-3 sm:p-6" onClick={() => closeSearch()}>
          <div
            ref={searchPanelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Quick search"
            onKeyDown={(event) => trapFocusWithinContainer(event, searchPanelRef.current)}
            className="mx-auto mt-12 w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-3 shadow-2xl dark:border-slate-700 dark:bg-slate-950"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
              <Search size={16} className="text-slate-400" />
              <input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={onSearchInputKeyDown}
                className="h-10 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-white"
                placeholder="Search pages like notifications, sections, or onboarding"
              />
              <button type="button" className="btn-secondary !gap-1 !px-2 !py-1 text-xs" onClick={() => closeSearch()}>
                <X size={12} /> Close
              </button>
            </div>

            <div className="mt-3">
              {searchQuery.trim() ? (
                quickSearchMatches.length ? (
                  <div className="space-y-1">
                    {quickSearchMatches.map((item: any, index: number) => (
                      <button
                        key={item.id}
                        type="button"
                        className={cn(
                          'flex w-full items-center justify-between rounded-2xl px-3 py-3 text-left transition',
                          index === activeSearchIndex
                            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                            : 'bg-slate-50 text-slate-700 hover:bg-slate-100 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                        )}
                        onMouseEnter={() => setActiveSearchIndex(index)}
                        onClick={() => openSearchMatch(item.path)}
                      >
                        <span>
                          <span className="block text-sm font-semibold">{item.label}</span>
                          <span className={cn('block text-xs', index === activeSearchIndex ? 'text-slate-200 dark:text-slate-700' : 'text-slate-500')}>
                            {item.groupLabel}
                          </span>
                        </span>
                        <span className={cn('text-xs', index === activeSearchIndex ? 'text-slate-200 dark:text-slate-700' : 'text-slate-400')}>
                          {item.path}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                    No matching pages found for "{searchQuery.trim()}".
                  </div>
                )
              ) : (
                favoriteShortcutItems.length || recentShortcutItems.length ? (
                  <div className="space-y-4">
                    {favoriteShortcutItems.length ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 px-1">
                          <Star size={14} className="text-amber-500" />
                          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                            Favorites
                          </p>
                        </div>
                        {renderShortcutRows(favoriteShortcutItems, true)}
                      </div>
                    ) : null}
                    {recentShortcutItems.length ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 px-1">
                          <History size={14} className="text-slate-400" />
                          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                            Recent Pages
                          </p>
                        </div>
                        {renderShortcutRows(recentShortcutItems, true)}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                    Start typing to jump to pages across your current workspace. Press <span className="font-semibold">/</span> any time to reopen search.
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
