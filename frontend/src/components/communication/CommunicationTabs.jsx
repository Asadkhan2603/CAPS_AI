import { NavLink } from 'react-router-dom';
import { cn } from '../../utils/cn';

const TABS = [
  { to: '/communication/feed', label: 'Feed' },
  { to: '/communication/announcements', label: 'Announcements' },
  { to: '/communication/messages', label: 'Messages' }
];

export default function CommunicationTabs() {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            cn(
              'rounded-xl px-4 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </div>
  );
}
