import { NavLink } from 'react-router-dom';
import { FEATURE_ACCESS } from '../../config/featureAccess';
import { useAuth } from '../../hooks/useAuth';
import { canAccessFeature } from '../../utils/permissions';
import { cn } from '../../utils/cn';

const BASE_TABS = [
  { to: '/communication/feed', label: 'Feed' },
  { to: '/communication/announcements', label: 'Announcements' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/communication/messages', label: 'Messages', badge: 'Planned' }
];

export default function CommunicationTabs() {
  const { user } = useAuth();
  const tabs = canAccessFeature(user, FEATURE_ACCESS.clubs)
    ? [
        ...BASE_TABS.slice(0, 3),
        { to: '/clubs?tab=announcements', label: 'Club Updates' },
        BASE_TABS[3]
      ]
    : BASE_TABS;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            cn(
              'rounded-xl px-4 py-2 text-sm font-medium transition-colors',
              'inline-flex items-center gap-2',
              isActive
                ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            )
          }
        >
          <span>{tab.label}</span>
          {tab.badge ? (
            <span className="rounded-full border border-current/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
              {tab.badge}
            </span>
          ) : null}
        </NavLink>
      ))}
    </div>
  );
}
