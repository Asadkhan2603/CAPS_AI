import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const items = [
  { to: '/admin/dashboard', label: 'Dashboard', requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'] },
  { to: '/admin/governance', label: 'Governance', requiredAdminTypes: ['super_admin', 'admin'] },
  { to: '/faculties', label: 'Academic Structure', requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'] },
  { to: '/students', label: 'Operations', requiredAdminTypes: ['super_admin', 'admin'] },
  { to: '/clubs', label: 'Clubs', requiredAdminTypes: ['super_admin', 'admin'] },
  { to: '/communication/announcements', label: 'Communication', requiredAdminTypes: ['super_admin', 'admin'] },
  { to: '/audit-logs', label: 'Compliance', requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
  { to: '/admin/analytics', label: 'Analytics', requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'] },
  { to: '/admin/system', label: 'System', requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
  { to: '/admin/recovery', label: 'Recovery', requiredAdminTypes: ['super_admin', 'admin'] },
  { to: '/admin/developer', label: 'Developer', requiredAdminTypes: ['super_admin'] }
];

export default function AdminDomainNav() {
  const { user } = useAuth();
  const adminType = user?.admin_type || 'admin';
  const visibleItems = items.filter((item) => item.requiredAdminTypes.includes(adminType));

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap gap-2">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `rounded-xl px-3 py-1.5 text-sm ${
                isActive
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </div>
  );
}
