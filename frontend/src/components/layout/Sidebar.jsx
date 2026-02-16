import { LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '../../utils/cn';

const mainItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/students', label: 'Students' },
  { to: '/subjects', label: 'Subjects' },
  { to: '/assignments', label: 'Assignments' },
  { to: '/submissions', label: 'Submissions' }
];

const adminItems = [
  { to: '/courses', label: 'Courses' },
  { to: '/years', label: 'Years' },
  { to: '/classes', label: 'Classes' },
  { to: '/sections', label: 'Sections' },
  { to: '/section-subjects', label: 'Section Subjects' }
];

export default function Sidebar({ user, collapsed, mobileOpen, onToggleCollapse, onCloseMobile, onLogout }) {
  const items = user?.role === 'admin' ? [...mainItems, ...adminItems] : mainItems;

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white/95 p-4 transition-transform duration-300 dark:border-slate-800 dark:bg-slate-900/95 lg:static lg:translate-x-0',
        collapsed ? 'lg:w-24' : 'lg:w-72',
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      <div className="mb-4 flex items-center justify-between">
        <div className={cn('transition-all', collapsed ? 'lg:opacity-0' : 'opacity-100')}>
          <p className="text-xs uppercase tracking-widest text-brand-500">CAPS AI</p>
          <h1 className="text-lg font-semibold">Control Center</h1>
        </div>
        <button className="btn-secondary !p-2" onClick={onToggleCollapse}>
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      <p className={cn('mb-3 text-xs text-slate-500 dark:text-slate-400', collapsed && 'lg:hidden')}>
        {user?.full_name} ({user?.role})
      </p>

      <nav className="flex-1 space-y-1 overflow-y-auto">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onCloseMobile}
            className={({ isActive }) =>
              cn(
                'block rounded-xl px-3 py-2 text-sm transition',
                isActive
                  ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <button className="btn-secondary mt-4 justify-start" onClick={onLogout}>
        <LogOut size={16} /> Logout
      </button>
    </aside>
  );
}
