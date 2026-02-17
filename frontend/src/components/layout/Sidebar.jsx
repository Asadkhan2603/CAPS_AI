import {
  LogOut,
  LayoutDashboard,
  ChartNoAxesCombined,
  GraduationCap,
  BookOpen,
  FileText,
  ClipboardCheck,
  CheckSquare,
  UserCheck,
  Megaphone,
  Bell,
  Users,
  CalendarDays,
  ScrollText,
  Shield,
  Library,
  CalendarRange,
  School,
  Layers,
  Network,
  Building2,
  GitBranch
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { canAccessFeature } from '../../utils/permissions';
import { FEATURE_ACCESS } from '../../config/featureAccess';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';

const mainItems = [
  { to: '/dashboard', label: 'Dashboard', featureKey: 'dashboard', icon: LayoutDashboard },
  { to: '/analytics', label: 'Analytics', featureKey: 'analytics', icon: ChartNoAxesCombined },
  { to: '/academic-structure', label: 'Academic Structure', featureKey: 'academicStructure', icon: Network },
  { to: '/students', label: 'Students', featureKey: 'students', icon: GraduationCap },
  { to: '/subjects', label: 'Subjects', featureKey: 'subjects', icon: BookOpen },
  { to: '/assignments', label: 'Assignments', featureKey: 'assignments', icon: FileText },
  { to: '/submissions', label: 'Submissions', featureKey: 'submissions', icon: ClipboardCheck },
  { to: '/review-tickets', label: 'Review Tickets', featureKey: 'reviewTickets', icon: ScrollText },
  { to: '/evaluations', label: 'Evaluations', featureKey: 'evaluations', icon: CheckSquare },
  { to: '/enrollments', label: 'Enrollments', featureKey: 'enrollments', icon: UserCheck },
  { to: '/notices', label: 'Notices', featureKey: 'notices', icon: Megaphone },
  { to: '/notifications', label: 'Notifications', featureKey: 'notifications', icon: Bell },
  { to: '/clubs', label: 'Clubs', featureKey: 'clubs', icon: Users },
  { to: '/club-events', label: 'Club Events', featureKey: 'clubEvents', icon: CalendarDays },
  { to: '/audit-logs', label: 'Audit Logs', featureKey: 'auditLogs', icon: Shield },
  { to: '/users', label: 'Users', featureKey: 'users', icon: Users }
];

const adminItems = [
  { to: '/courses', label: 'Courses', featureKey: 'courses', icon: Library },
  { to: '/departments', label: 'Departments', featureKey: 'departments', icon: Building2 },
  { to: '/branches', label: 'Branches', featureKey: 'branches', icon: GitBranch },
  { to: '/years', label: 'Years', featureKey: 'years', icon: CalendarRange },
  { to: '/classes', label: 'Classes', featureKey: 'classes', icon: School },
  { to: '/sections', label: 'Sections', featureKey: 'sections', icon: Layers },
  { to: '/section-subjects', label: 'Section Subjects', featureKey: 'sectionSubjects', icon: Layers }
];

export default function Sidebar({ user, collapsed, mobileOpen, onCloseMobile, onLogout }) {
  const { pushToast } = useToast();
  const role = user?.role;
  const isAdmin = role === 'admin';
  const [hasLogo, setHasLogo] = useState(false);
  const [logoVersion, setLogoVersion] = useState('');
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const logoInputRef = useRef(null);
  const visibleMainItems = mainItems.filter((item) =>
    canAccessFeature(user, FEATURE_ACCESS[item.featureKey])
  );
  const visibleAdminItems = adminItems.filter((item) =>
    canAccessFeature(user, FEATURE_ACCESS[item.featureKey])
  );
  const items = role === 'admin' ? [...visibleMainItems, ...visibleAdminItems] : visibleMainItems;
  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);
  const logoUrl = hasLogo
    ? `${backendBaseUrl}/api/v1/branding/logo${logoVersion ? `?v=${encodeURIComponent(logoVersion)}` : ''}`
    : null;

  useEffect(() => {
    async function loadLogoMeta() {
      try {
        const response = await apiClient.get('/branding/logo/meta');
        if (response.data?.has_logo) {
          setHasLogo(true);
          setLogoVersion(String(response.data.updated_at || Date.now()));
        } else {
          setHasLogo(false);
          setLogoVersion('');
        }
      } catch {
        setHasLogo(false);
        setLogoVersion('');
      }
    }
    loadLogoMeta();
  }, []);

  async function onUploadLogo(file) {
    if (!file || !isAdmin) {
      return;
    }
    try {
      setUploadingLogo(true);
      const multipart = new FormData();
      multipart.append('file', file);
      const response = await apiClient.post('/branding/logo', multipart, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setHasLogo(true);
      setLogoVersion(String(response.data?.updated_at || Date.now()));
      pushToast({ title: 'Logo updated', description: 'Brand logo uploaded successfully.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Upload failed', description: formatApiError(err, 'Failed to upload logo'), variant: 'error' });
    } finally {
      setUploadingLogo(false);
      if (logoInputRef.current) {
        logoInputRef.current.value = '';
      }
    }
  }

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white/95 p-4 transition-transform duration-300 dark:border-slate-800 dark:bg-slate-900/95 lg:static lg:translate-x-0',
        collapsed ? 'lg:w-24' : 'lg:w-72',
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      <div className="mb-4">
        <div className={cn('transition-all', collapsed ? 'lg:opacity-0' : 'opacity-100')}>
          <p className="text-xs uppercase tracking-widest text-brand-500">CAPS AI</p>
          <h1 className="text-lg font-semibold">Control Center</h1>
        </div>
        <div className={cn('mt-3', collapsed && 'hidden')}>
          {logoUrl ? (
            <img
              src={logoUrl}
              alt="Institute Logo"
              className="h-20 w-full rounded-xl border border-slate-200 object-contain p-2 dark:border-slate-700"
            />
          ) : (
            <div className="flex h-20 w-full items-center justify-center rounded-xl border border-dashed border-slate-300 text-xs font-semibold text-slate-500 dark:border-slate-700 dark:text-slate-400">
              COLLEGE / UNIVERSITY LOGO
            </div>
          )}
        </div>
        {isAdmin ? (
          <div className={cn('mt-2 flex justify-center', collapsed && 'hidden')}>
            <input
              ref={logoInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.webp,.svg"
              className="hidden"
              onChange={(e) => onUploadLogo(e.target.files?.[0])}
            />
            <button
              type="button"
              className="btn-secondary !px-2 !py-1 text-xs"
              onClick={() => logoInputRef.current?.click()}
              disabled={uploadingLogo}
            >
              {uploadingLogo ? 'Uploading...' : 'Upload Logo'}
            </button>
          </div>
        ) : null}
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
            title={item.label}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition',
                isActive
                  ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
                collapsed && 'justify-center px-2'
              )
            }
          >
            {item.icon ? <item.icon size={16} /> : null}
            <span className={cn(collapsed && 'lg:hidden')}>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <button className="btn-secondary mt-4 justify-start" onClick={onLogout}>
        <LogOut size={16} /> Logout
      </button>
    </aside>
  );
}
