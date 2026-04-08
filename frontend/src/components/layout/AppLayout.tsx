import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { CSSProperties } from 'react';
import Toast from '../ui/Toast';
import Header from './Header';
import MainContent from './MainContent';
import Sidebar from './Sidebar';
import type { SidebarState } from './types';

type AppLayoutProps = {
  user: any;
  sessionBootstrap?: any;
  isDark: boolean;
  onToggleTheme: () => void;
  onLogout: () => void;
  toasts: any[];
  onDismissToast: (id: string) => void;
  locationKey: string;
  children: ReactNode;
};

const DESKTOP_QUERY = '(min-width: 1024px)';
const TABLET_QUERY = '(min-width: 768px) and (max-width: 1023px)';
const SIDEBAR_PIN_KEY = 'caps.sidebar.pinned';
const HEADER_HEIGHT_PX = 68;
const TABLET_RAIL_WIDTH_PX = 72;

function readPinnedState() {
  if (typeof window === 'undefined') {
    return true;
  }
  const storedValue = window.localStorage.getItem(SIDEBAR_PIN_KEY);
  if (storedValue === null) {
    return true;
  }
  return storedValue === 'true';
}

export default function AppLayout({
  user,
  sessionBootstrap,
  isDark,
  onToggleTheme,
  onLogout,
  toasts,
  onDismissToast,
  locationKey,
  children
}: AppLayoutProps) {
  const [isPinned, setIsPinned] = useState<boolean>(readPinnedState);
  const [isHovered, setIsHovered] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const navTriggerRef = useRef<HTMLElement | null>(null);
  const previousMobileOpenRef = useRef(false);
  const [isTablet, setIsTablet] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.matchMedia(TABLET_QUERY).matches;
  });
  const [isDesktop, setIsDesktop] = useState(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    return window.matchMedia(DESKTOP_QUERY).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const mediaQuery = window.matchMedia(DESKTOP_QUERY);
    const tabletQuery = window.matchMedia(TABLET_QUERY);
    const onMediaChange = (event: MediaQueryListEvent) => {
      setIsDesktop(event.matches);
    };
    const onTabletChange = (event: MediaQueryListEvent) => {
      setIsTablet(event.matches);
    };

    setIsDesktop(mediaQuery.matches);
    setIsTablet(tabletQuery.matches);
    mediaQuery.addEventListener('change', onMediaChange);
    tabletQuery.addEventListener('change', onTabletChange);
    return () => {
      mediaQuery.removeEventListener('change', onMediaChange);
      tabletQuery.removeEventListener('change', onTabletChange);
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(SIDEBAR_PIN_KEY, String(isPinned));
  }, [isPinned]);

  useEffect(() => {
    if (isDesktop) {
      setIsMobileOpen(false);
      return;
    }
    setIsHovered(false);
  }, [isDesktop]);

  useEffect(() => {
    if (!isDesktop) {
      setIsMobileOpen(false);
    }
  }, [isDesktop, locationKey]);

  useEffect(() => {
    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsMobileOpen(false);
      }
    }
    window.addEventListener('keydown', onEscape);
    return () => window.removeEventListener('keydown', onEscape);
  }, []);

  useEffect(() => {
    if (previousMobileOpenRef.current && !isMobileOpen) {
      const timer = window.setTimeout(() => {
        navTriggerRef.current?.focus();
      }, 0);
      previousMobileOpenRef.current = isMobileOpen;
      return () => window.clearTimeout(timer);
    }
    previousMobileOpenRef.current = isMobileOpen;
    return undefined;
  }, [isMobileOpen]);

  function toggleNavigationPanel(trigger?: HTMLElement | null) {
    if (trigger) {
      navTriggerRef.current = trigger;
    }
    setIsMobileOpen((prev) => !prev);
  }

  const sidebarState: SidebarState = useMemo(() => {
    const isExpanded = isDesktop ? (isPinned || isHovered) : isMobileOpen;
    return {
      isPinned,
      isHovered,
      isMobileOpen,
      isTablet,
      isDesktop,
      isExpanded
    };
  }, [isDesktop, isHovered, isMobileOpen, isPinned, isTablet]);

  const desktopContentOffset = sidebarState.isExpanded ? 250 : 64;
  const contentShellStyle: CSSProperties = {
    paddingTop: HEADER_HEIGHT_PX
  };
  if (isDesktop) {
    contentShellStyle.paddingLeft = desktopContentOffset;
  } else if (isTablet) {
    contentShellStyle.paddingLeft = TABLET_RAIL_WIDTH_PX;
  }

  return (
    <div className="relative h-screen overflow-hidden bg-[radial-gradient(1200px_500px_at_15%_-10%,rgba(14,165,233,0.18),transparent),radial-gradient(900px_500px_at_90%_0%,rgba(99,102,241,0.18),transparent)] dark:bg-[radial-gradient(1200px_520px_at_12%_-8%,rgba(56,189,248,0.18),transparent),radial-gradient(900px_560px_at_88%_0%,rgba(99,102,241,0.22),transparent),linear-gradient(180deg,rgba(2,6,23,0.96),rgba(8,17,31,0.98))]">
      <Header
        user={user}
        initialNotificationCount={sessionBootstrap?.unread_notification_count}
        initialLogoVersion={sessionBootstrap?.branding?.updated_at ? String(sessionBootstrap.branding.updated_at) : ''}
        isDark={isDark}
        onToggleTheme={onToggleTheme}
        onToggleMobileNavigation={(trigger) => toggleNavigationPanel(trigger)}
        isMobileNavigationOpen={isMobileOpen}
        onToggleDesktopSidebar={() => setIsPinned((prev) => !prev)}
        isDesktopSidebarExpanded={sidebarState.isExpanded}
        onLogout={onLogout}
        headerHeight={HEADER_HEIGHT_PX}
      />

      <Sidebar
        user={user}
        sidebarState={sidebarState}
        onHoverChange={setIsHovered}
        onTogglePin={() => setIsPinned((prev) => !prev)}
        onOpenCompactPanel={(trigger) => {
          if (!isMobileOpen) {
            toggleNavigationPanel(trigger);
          }
        }}
        onCloseMobile={() => setIsMobileOpen(false)}
        onLogout={onLogout}
        headerHeight={HEADER_HEIGHT_PX}
      />

      <div className="h-full transition-[padding-left] duration-250 ease-in-out" style={contentShellStyle}>
        <MainContent routeKey={locationKey} headerHeight={HEADER_HEIGHT_PX}>
          {children}
        </MainContent>
      </div>

      <Toast toasts={toasts} onDismiss={onDismissToast} />
    </div>
  );
}
