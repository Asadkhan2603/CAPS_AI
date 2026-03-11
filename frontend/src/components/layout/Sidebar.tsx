import {
  Bell,
  ClipboardCheck,
  FileText,
  GraduationCap,
  HelpCircle,
  House,
  LogOut,
  Megaphone,
  Pin,
  PinOff,
  School,
  Shield,
  UserCircle2,
  Users,
  Wrench
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
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
  operations: Wrench,
  setup: School,
  profile: UserCircle2
};

type SidebarProps = {
  user: any;
  sidebarState: SidebarState;
  onHoverChange: (hovered: boolean) => void;
  onTogglePin: () => void;
  onCloseMobile: () => void;
  onLogout: () => void;
  headerHeight: number;
};

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
  onCloseMobile,
  onLogout,
  headerHeight
}: SidebarProps) {
  const location = useLocation();
  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const hoverOpenTimerRef = useRef<number | null>(null);
  const hoverCloseTimerRef = useRef<number | null>(null);
  const visibleGroups = useMemo(
    () => getVisibleNavigationGroups(user) as NavGroup[],
    [user]
  );
  const collapsed = sidebarState.isDesktop && !sidebarState.isExpanded;
  const roleLabel = useMemo(
    () => titleize(user?.admin_type || user?.role || 'member'),
    [user?.admin_type, user?.role]
  );

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
        hoverOpenTimerRef.current = null;
      }
      if (hoverCloseTimerRef.current !== null) {
        window.clearTimeout(hoverCloseTimerRef.current);
        hoverCloseTimerRef.current = null;
      }
    };
  }, []);

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

  return (
    <aside
      onMouseEnter={() => handleHover(true)}
      onMouseLeave={() => handleHover(false)}
      className={cn(
        'fixed bottom-0 left-0 z-40 flex flex-col border-r border-slate-200 bg-white/95 transition-[width,transform] duration-250 ease-in-out dark:border-slate-800 dark:bg-slate-900/95',
        collapsed ? 'w-16' : 'w-[250px]',
        sidebarState.isDesktop
          ? 'translate-x-0'
          : sidebarState.isMobileOpen
            ? 'translate-x-0 shadow-2xl'
            : '-translate-x-full'
      )}
      style={{ top: headerHeight }}
    >
      <div className="border-b border-slate-200 p-2.5 dark:border-slate-800">
        <div className={cn('relative flex items-center gap-2 rounded-xl bg-slate-100/80 p-2 dark:bg-slate-800/60', collapsed && 'justify-center')}>
          {!collapsed ? (
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

          {sidebarState.isDesktop && !collapsed ? (
            <button
              type="button"
              onClick={onTogglePin}
              className={cn(
                'rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800',
                collapsed ? 'absolute -right-1 -top-1' : ''
              )}
              title={sidebarState.isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
            >
              {sidebarState.isPinned ? <PinOff size={14} /> : <Pin size={14} />}
            </button>
          ) : null}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-1.5 py-2">
        {collapsed ? (
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
                  to={groupPath}
                  active={isGroupActive(group)}
                  onClick={handleNavClick}
                />
              );
            })}
          </div>
        ) : (
          <div className="space-y-2">
            {visibleGroups.map((group) => {
              const GroupIcon = groupIconMap[group.key as keyof typeof groupIconMap] || group.items[0]?.icon || House;
              const hasChildren = group.items.length > 1;
              const headerPath = getWorkspaceItemPath(group.key, group.items[0].to);
              const isOpen = !!openGroups[group.key];
              const groupActive = isGroupActive(group);

              return (
                <div key={group.key} className="rounded-xl border border-slate-200/80 bg-white/60 p-1.5 dark:border-slate-800 dark:bg-slate-950/30">
                  <SidebarItem
                    icon={GroupIcon}
                    label={group.label}
                    tooltip={group.label}
                    collapsed={false}
                    to={hasChildren ? undefined : headerPath}
                    onClick={hasChildren ? () => setOpenGroups((prev) => ({ ...prev, [group.key]: !prev[group.key] })) : handleNavClick}
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
        )}
      </div>

      <div className="border-t border-slate-200 p-2 dark:border-slate-800">
        <div className={cn('space-y-1', collapsed && 'flex flex-col items-center')}>
          <SidebarItem
            icon={HelpCircle}
            label="Help"
            tooltip="Help"
            collapsed={collapsed}
            to="/workspace/overview/dashboard"
            onClick={handleNavClick}
          />
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
    </aside>
  );
}
