import { ChevronDown, ChevronRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../utils/cn';

type SidebarItemProps = {
  icon?: LucideIcon;
  label: string;
  active?: boolean;
  collapsed: boolean;
  tooltip?: string;
  hasChildren?: boolean;
  expanded?: boolean;
  to?: string;
  onClick?: () => void;
  className?: string;
};

export default function SidebarItem({
  icon: Icon,
  label,
  active = false,
  collapsed,
  tooltip,
  hasChildren = false,
  expanded = false,
  to,
  onClick,
  className
}: SidebarItemProps) {
  const sharedClassName = cn(
    'group/item relative flex w-full items-center gap-3 rounded-xl border-l-[3px] px-2.5 py-2 text-sm transition-colors',
    collapsed ? 'justify-center border-l-transparent px-2' : 'border-l-transparent',
    active
      ? 'border-l-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white',
    className
  );

  const content = (
    <>
      {Icon ? <Icon size={17} className="shrink-0" /> : null}
      <span
        className={cn(
          'min-w-0 truncate whitespace-nowrap font-medium transition-all duration-200',
          collapsed ? 'w-0 -translate-x-1 opacity-0' : 'w-auto translate-x-0 opacity-100'
        )}
      >
        {label}
      </span>
      {!collapsed && hasChildren ? (
        <span className="ml-auto shrink-0 text-slate-500 dark:text-slate-400">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
      ) : null}

      {collapsed && tooltip ? (
        <span className="pointer-events-none absolute left-full ml-3 hidden min-w-max rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 shadow-md group-hover/item:block dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
          {tooltip}
        </span>
      ) : null}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={sharedClassName} onClick={onClick} title={collapsed ? tooltip || label : undefined}>
        {content}
      </Link>
    );
  }

  return (
    <button type="button" className={sharedClassName} onClick={onClick} title={collapsed ? tooltip || label : undefined}>
      {content}
    </button>
  );
}
