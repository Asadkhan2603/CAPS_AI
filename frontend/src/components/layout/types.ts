import type { LucideIcon } from 'lucide-react';

export type SidebarState = {
  isPinned: boolean;
  isHovered: boolean;
  isMobileOpen: boolean;
  isDesktop: boolean;
  isExpanded: boolean;
};

export type NavItem = {
  to: string;
  label: string;
  icon?: LucideIcon;
  children?: NavItem[];
};

export type NavGroup = {
  key: string;
  label: string;
  items: NavItem[];
};
