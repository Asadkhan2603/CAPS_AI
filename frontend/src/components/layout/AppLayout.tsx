import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { CSSProperties } from 'react';
import Toast from '../ui/Toast';
import Header from './Header';
import MainContent from './MainContent';
import Sidebar from './Sidebar';
import type { SidebarState } from './types';

type AppLayoutProps = {
  user: any;
  isDark: boolean;
  onToggleTheme: () => void;
  onLogout: () => void;
  toasts: any[];
  onDismissToast: (id: string) => void;
  locationKey: string;
  children: ReactNode;
};

const DESKTOP_QUERY = '(min-width: 1024px)';
const SIDEBAR_PIN_KEY = 'caps.sidebar.pinned';
const HEADER_HEIGHT_PX = 68;

function readPinnedState() {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.localStorage.getItem(SIDEBAR_PIN_KEY) === 'true';
}

export default function AppLayout({
  user,
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
    const onMediaChange = (event: MediaQueryListEvent) => {
      setIsDesktop(event.matches);
    };

    setIsDesktop(mediaQuery.matches);
    mediaQuery.addEventListener('change', onMediaChange);
    return () => {
      mediaQuery.removeEventListener('change', onMediaChange);
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
    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsMobileOpen(false);
      }
    }
    window.addEventListener('keydown', onEscape);
    return () => window.removeEventListener('keydown', onEscape);
  }, []);

  const sidebarState: SidebarState = useMemo(() => {
    const isExpanded = isDesktop ? (isPinned || isHovered) : isMobileOpen;
    return {
      isPinned,
      isHovered,
      isMobileOpen,
      isDesktop,
      isExpanded
    };
  }, [isDesktop, isHovered, isMobileOpen, isPinned]);

  const desktopContentOffset = sidebarState.isExpanded ? 250 : 64;
  const contentShellStyle: CSSProperties = {
    paddingTop: HEADER_HEIGHT_PX
  };
  if (isDesktop) {
    contentShellStyle.paddingLeft = desktopContentOffset;
  }

  return (
    <div className="relative h-screen overflow-hidden bg-[radial-gradient(1200px_500px_at_15%_-10%,rgba(14,165,233,0.18),transparent),radial-gradient(900px_500px_at_90%_0%,rgba(99,102,241,0.18),transparent)] dark:bg-[radial-gradient(1200px_520px_at_12%_-8%,rgba(56,189,248,0.18),transparent),radial-gradient(900px_560px_at_88%_0%,rgba(99,102,241,0.22),transparent),linear-gradient(180deg,rgba(2,6,23,0.96),rgba(8,17,31,0.98))]">
      <Header
        user={user}
        isDark={isDark}
        onToggleTheme={onToggleTheme}
        onOpenMobile={() => setIsMobileOpen(true)}
        onLogout={onLogout}
        headerHeight={HEADER_HEIGHT_PX}
      />

      <Sidebar
        user={user}
        sidebarState={sidebarState}
        onHoverChange={setIsHovered}
        onTogglePin={() => setIsPinned((prev) => !prev)}
        onCloseMobile={() => setIsMobileOpen(false)}
        onLogout={onLogout}
        headerHeight={HEADER_HEIGHT_PX}
      />

      <div className="h-full transition-[padding-left] duration-250 ease-in-out" style={contentShellStyle}>
        <MainContent routeKey={locationKey} headerHeight={HEADER_HEIGHT_PX}>
          {children}
        </MainContent>
      </div>

      {!isDesktop && isMobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-slate-950/45"
          onClick={() => setIsMobileOpen(false)}
          aria-label="Close navigation drawer"
        />
      ) : null}

      <Toast toasts={toasts} onDismiss={onDismissToast} />
    </div>
  );
}
