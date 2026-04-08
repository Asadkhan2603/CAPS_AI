import {
  Bell,
  ClipboardCheck,
  PanelLeftClose,
  FileText,
  GraduationCap,
  House,
  LogOut,
  Megaphone,
  Pin,
  PinOff,
  School,
  Shield,
  UserCircle2,
  Users,
  Wrench,
  X
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type {
  CSSProperties,
  KeyboardEvent as ReactKeyboardEvent,
  TouchEvent as ReactTouchEvent,
  WheelEvent as ReactWheelEvent
} from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { getVisibleNavigationGroups, getWorkspaceItemPath } from '../../config/navigationGroups';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import SidebarItem from './SidebarItem';
import type { NavGroup, SidebarState } from './types';

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
  administration: Shield,
  operations: Wrench,
  system: Wrench,
  setup: School,
  profile: UserCircle2
};

type SidebarProps = {
  user: any;
  sidebarState: SidebarState;
  onHoverChange: (hovered: boolean) => void;
  onTogglePin: () => void;
  onOpenCompactPanel: (trigger?: HTMLElement | null) => void;
  onCloseMobile: () => void;
  onLogout: () => void;
  headerHeight: number;
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

function titleize(value: unknown) {
  if (!value) {
    return '';
  }
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export default function Sidebar({
  user,
  sidebarState,
  onHoverChange,
  onTogglePin,
  onOpenCompactPanel,
  onCloseMobile,
  onLogout,
  headerHeight
}: SidebarProps) {
  const location = useLocation();
  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const compactPanelRef = useRef<HTMLElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const hoverOpenTimerRef = useRef<number | null>(null);
  const hoverCloseTimerRef = useRef<number | null>(null);
  const visibleGroups = useMemo(() => getVisibleNavigationGroups(user) as NavGroup[], [user]);
  const roleLabel = useMemo(
    () => titleize(user?.admin_type || user?.role || 'member'),
    [user?.admin_type, user?.role]
  );
  const hasDesktopSidebar = sidebarState.isDesktop;
  const hasTabletRail = sidebarState.isTablet;
  const isCompactPanelOpen = !sidebarState.isDesktop && sidebarState.isExpanded;
  const isTabletPanelOpen = sidebarState.isTablet && sidebarState.isExpanded;
  const isDesktopCollapsed = sidebarState.isDesktop && !sidebarState.isExpanded;
  const baseCollapsed = hasTabletRail || isDesktopCollapsed;
  const baseWidthClass = baseCollapsed ? 'w-[72px]' : 'w-[250px]';
  const basePanelStyle: CSSProperties = {
    top: headerHeight,
    height: `calc(100dvh - ${headerHeight}px)`
  };
  const compactPanelStyle: CSSProperties = {
    top: headerHeight,
    left: isTabletPanelOpen ? 72 : 0,
    width: isTabletPanelOpen ? 250 : Math.min(280, typeof window === 'undefined' ? 280 : window.innerWidth - 24),
    height: `calc(100dvh - ${headerHeight}px)`
  };
  const compactBackdropStyle: CSSProperties = {
    top: headerHeight,
    left: isTabletPanelOpen ? 72 : 0
  };
  const scrollRegionStyle: CSSProperties = {
    WebkitOverflowScrolling: 'touch'
  };

  useEffect(() => {
    const activeGroup = visibleGroups.find((group) =>
      group.items.some((item) => {
        const workspacePath = getWorkspaceItemPath(group.key, item.to);
        return (
          location.pathname === workspacePath ||
          location.pathname.startsWith(`${workspacePath}/`) ||
          location.pathname === item.to ||
          location.pathname.startsWith(`${item.to}/`)
        );
      })
    );
    if (activeGroup) {
      setOpenGroups((prev) => ({ ...prev, [activeGroup.key]: true }));
    }
  }, [location.pathname, visibleGroups]);

  useEffect(() => {
    return () => {
      if (hoverOpenTimerRef.current !== null) {
        window.clearTimeout(hoverOpenTimerRef.current);
      }
      if (hoverCloseTimerRef.current !== null) {
        window.clearTimeout(hoverCloseTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isCompactPanelOpen) {
      return;
    }
    const timer = window.setTimeout(() => {
      const focusableElements = getFocusableElements(compactPanelRef.current);
      (closeButtonRef.current || focusableElements[0])?.focus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [isCompactPanelOpen]);

  useEffect(() => {
    if (!isCompactPanelOpen || typeof document === 'undefined' || typeof window === 'undefined') {
      return undefined;
    }

    const scrollY = window.scrollY;
    const { body, documentElement } = document;
    const previousBodyPosition = body.style.position;
    const previousBodyTop = body.style.top;
    const previousBodyLeft = body.style.left;
    const previousBodyRight = body.style.right;
    const previousBodyWidth = body.style.width;
    const previousBodyOverflow = body.style.overflow;
    const previousHtmlOverflow = documentElement.style.overflow;
    const previousHtmlOverscroll = documentElement.style.overscrollBehavior;

    body.style.position = 'fixed';
    body.style.top = `-${scrollY}px`;
    body.style.left = '0';
    body.style.right = '0';
    body.style.width = '100%';
    body.style.overflow = 'hidden';
    documentElement.style.overflow = 'hidden';
    documentElement.style.overscrollBehavior = 'none';

    return () => {
      body.style.position = previousBodyPosition;
      body.style.top = previousBodyTop;
      body.style.left = previousBodyLeft;
      body.style.right = previousBodyRight;
      body.style.width = previousBodyWidth;
      body.style.overflow = previousBodyOverflow;
      documentElement.style.overflow = previousHtmlOverflow;
      documentElement.style.overscrollBehavior = previousHtmlOverscroll;
      window.scrollTo(0, scrollY);
    };
  }, [isCompactPanelOpen]);

  function isItemActive(groupKey: string, to: string) {
    const workspacePath = getWorkspaceItemPath(groupKey, to);
    return (
      location.pathname === workspacePath ||
      location.pathname.startsWith(`${workspacePath}/`) ||
      location.pathname === to ||
      location.pathname.startsWith(`${to}/`)
    );
  }

  function isGroupActive(group: NavGroup) {
    return group.items.some((item) => isItemActive(group.key, item.to));
  }

  function handleHover(hovered: boolean) {
    if (!sidebarState.isDesktop || sidebarState.isPinned) {
      return;
    }
    if (hoverOpenTimerRef.current !== null) {
      window.clearTimeout(hoverOpenTimerRef.current);
      hoverOpenTimerRef.current = null;
    }
    if (hoverCloseTimerRef.current !== null) {
      window.clearTimeout(hoverCloseTimerRef.current);
      hoverCloseTimerRef.current = null;
    }

    if (hovered) {
      hoverOpenTimerRef.current = window.setTimeout(() => {
        onHoverChange(true);
        hoverOpenTimerRef.current = null;
      }, 40);
      return;
    }

    hoverCloseTimerRef.current = window.setTimeout(() => {
      onHoverChange(false);
      hoverCloseTimerRef.current = null;
    }, 180);
  }

  function handleNavClick() {
    if (!sidebarState.isDesktop) {
      onCloseMobile();
    }
  }

  function handleCollapsedGroupClick(groupKey: string) {
    if (sidebarState.isTablet) {
      setOpenGroups((prev) => ({ ...prev, [groupKey]: true }));
      onOpenCompactPanel(document.activeElement as HTMLElement | null);
    }
  }

  function closeCompactNavigation() {
    onCloseMobile();
  }

  function preventBackdropScroll(
    event: ReactTouchEvent<HTMLButtonElement> | ReactWheelEvent<HTMLButtonElement>
  ) {
    event.preventDefault();
    event.stopPropagation();
  }

  function renderNavigationContent(collapsed: boolean) {
    if (collapsed) {
      return (
        <div className="space-y-1">
          {visibleGroups.map((group) => {
            const GroupIcon = groupIconMap[group.key as keyof typeof groupIconMap] || group.items[0]?.icon || House;
            const groupPath = getWorkspaceItemPath(group.key, group.items[0].to);
            return (
              <SidebarItem
                key={group.key}
                icon={GroupIcon}
                label={group.label}
                tooltip={group.label}
                collapsed
                to={sidebarState.isTablet ? undefined : groupPath}
                active={isGroupActive(group)}
                onClick={sidebarState.isTablet ? () => handleCollapsedGroupClick(group.key) : undefined}
              />
            );
          })}
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {visibleGroups.map((group) => {
          const GroupIcon = groupIconMap[group.key as keyof typeof groupIconMap] || group.items[0]?.icon || House;
          const hasChildren = group.items.length > 1;
          const headerPath = getWorkspaceItemPath(group.key, group.items[0].to);
          const isOpen = !!openGroups[group.key];
          const groupActive = isGroupActive(group);

          return (
            <div
              key={group.key}
              className={cn(
                'rounded-xl border p-1.5 transition-colors duration-200',
                isOpen || groupActive
                  ? 'border-brand-200 bg-brand-50/80 shadow-sm dark:border-brand-700/60 dark:bg-brand-900/20'
                  : 'border-slate-200/80 bg-white/90 dark:border-slate-800 dark:bg-slate-950/70'
              )}
            >
              <SidebarItem
                icon={GroupIcon}
                label={group.label}
                tooltip={group.label}
                collapsed={false}
                to={hasChildren ? undefined : headerPath}
                onClick={
                  hasChildren
                    ? () => setOpenGroups((prev) => ({ ...prev, [group.key]: !prev[group.key] }))
                    : handleNavClick
                }
                active={groupActive}
                hasChildren={hasChildren}
                expanded={isOpen}
              />

              {hasChildren && isOpen ? (
                <div className="mt-1 space-y-0.5 border-l border-slate-200 pl-3 dark:border-slate-800">
                  {group.items.map((item) => (
                    <SidebarItem
                      key={`${group.key}-${item.to}`}
                      icon={item.icon}
                      label={item.label}
                      tooltip={item.label}
                      collapsed={false}
                      to={getWorkspaceItemPath(group.key, item.to)}
                      onClick={handleNavClick}
                      active={isItemActive(group.key, item.to)}
                      className="border-l-0 text-[13px]"
                    />
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    );
  }

  function renderFooter(collapsed: boolean) {
    return (
      <div className="border-t border-slate-200 p-2 dark:border-slate-800">
        <div className={cn('space-y-1', collapsed && 'flex flex-col items-center')}>
          <SidebarItem
            icon={LogOut}
            label="Logout"
            tooltip="Logout"
            collapsed={collapsed}
            onClick={onLogout}
          />
          {!collapsed ? (
            <div className="px-3 pt-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                CAPS Layout
              </p>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  const baseSidebar = hasDesktopSidebar || hasTabletRail ? (
    <aside
      onMouseEnter={() => handleHover(true)}
      onMouseLeave={() => handleHover(false)}
      className={cn(
        'fixed left-0 z-40 flex min-h-0 flex-col overscroll-contain border-r border-slate-200 transition-[width] duration-250 ease-in-out dark:border-slate-800',
        baseWidthClass,
        hasDesktopSidebar ? 'bg-white/95 dark:bg-slate-900/95' : 'bg-white dark:bg-slate-900'
      )}
      style={basePanelStyle}
    >
      <div className="border-b border-slate-200 p-2.5 dark:border-slate-800">
        <div className={cn('relative flex items-center gap-2 rounded-xl bg-slate-100/80 p-2 dark:bg-slate-800/60', baseCollapsed && 'justify-center')}>
          {!baseCollapsed ? (
            <>
              {avatarSrc ? (
                <img src={avatarSrc} alt="Profile" className="h-10 w-10 rounded-lg border border-slate-200 object-cover dark:border-slate-700" />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                  <UserCircle2 size={18} />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {user?.full_name || 'User'}
                </p>
                <p className="truncate text-[11px] text-slate-500 dark:text-slate-400">{roleLabel}</p>
              </div>
            </>
          ) : avatarSrc ? (
            <img src={avatarSrc} alt="Profile" className="h-9 w-9 rounded-lg border border-slate-200 object-cover dark:border-slate-700" />
          ) : (
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
              <UserCircle2 size={18} />
            </div>
          )}

          {hasDesktopSidebar && !baseCollapsed ? (
            <button
              type="button"
              onClick={onTogglePin}
              className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              title={sidebarState.isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
            >
              {sidebarState.isPinned ? <PinOff size={14} /> : <Pin size={14} />}
            </button>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1.5 py-2" style={scrollRegionStyle}>
        {renderNavigationContent(baseCollapsed)}
      </div>

      {renderFooter(baseCollapsed)}
    </aside>
  ) : null;

  const compactDrawer =
    isCompactPanelOpen && typeof document !== 'undefined'
      ? createPortal(
          <div className="fixed inset-x-0 bottom-0 z-[90]" style={{ top: headerHeight }}>
            <button
              type="button"
              className="absolute inset-0 bg-slate-950/55 backdrop-blur-[1.5px]"
              style={compactBackdropStyle}
              onClick={closeCompactNavigation}
              onTouchMove={preventBackdropScroll}
              onWheel={preventBackdropScroll}
              aria-label={isTabletPanelOpen ? 'Close navigation panel' : 'Close navigation drawer'}
            />

            <aside
              ref={compactPanelRef}
              role="dialog"
              aria-modal="true"
              aria-label={isTabletPanelOpen ? 'Navigation panel' : 'Navigation drawer'}
              onKeyDown={(event) => trapFocusWithinContainer(event, compactPanelRef.current)}
              className="absolute flex min-h-0 flex-col overflow-hidden border-r border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
              style={compactPanelStyle}
            >
              <div className="border-b border-slate-200 p-2.5 dark:border-slate-800">
                <div className="relative flex items-center gap-2 rounded-xl bg-slate-100 p-2 dark:bg-slate-800">
                  {avatarSrc ? (
                    <img src={avatarSrc} alt="Profile" className="h-10 w-10 rounded-lg border border-slate-200 object-cover dark:border-slate-700" />
                  ) : (
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                      <UserCircle2 size={18} />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {user?.full_name || 'User'}
                    </p>
                    <p className="truncate text-[11px] text-slate-500 dark:text-slate-400">{roleLabel}</p>
                  </div>
                  <button
                    ref={closeButtonRef}
                    type="button"
                    onClick={closeCompactNavigation}
                    className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                    title={isTabletPanelOpen ? 'Collapse navigation panel' : 'Close navigation drawer'}
                    aria-label={isTabletPanelOpen ? 'Collapse navigation panel' : 'Close navigation drawer'}
                  >
                    {isTabletPanelOpen ? <PanelLeftClose size={14} /> : <X size={14} />}
                  </button>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1.5 py-2" style={scrollRegionStyle}>
                {renderNavigationContent(false)}
              </div>

              {renderFooter(false)}
            </aside>
          </div>,
          document.body
        )
      : null;

  return (
    <>
      {baseSidebar}
      {compactDrawer}
    </>
  );
}
