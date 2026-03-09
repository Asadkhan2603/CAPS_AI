import {
  LogOut,
  LayoutDashboard,
  ChartNoAxesCombined,
  ChevronDown,
  ChevronRight,
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
  Network,
  Building2,
  GitBranch,
  Wrench,
  History
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { canAccessFeature } from '../../utils/permissions';
import { FEATURE_ACCESS } from '../../config/featureAccess';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';

const groupedItems = [
  {
    key: 'adminPanel',
    label: 'Admin Panel',
    items: [
      { to: '/admin/dashboard', label: 'Admin Dashboard', featureKey: 'adminDashboard', icon: LayoutDashboard, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'] },
      { to: '/admin/governance', label: 'Governance', featureKey: 'adminGovernance', icon: Shield, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/admin/academic-structure', label: 'Academic Structure', featureKey: 'adminAcademicStructure', icon: Network, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'] },
      { to: '/admin/operations', label: 'Operations', featureKey: 'adminOperations', icon: Wrench, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/admin/clubs', label: 'Clubs', featureKey: 'adminClubs', icon: Users, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/admin/communication', label: 'Communication', featureKey: 'adminCommunication', icon: Megaphone, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/admin/compliance', label: 'Compliance', featureKey: 'adminCompliance', icon: Shield, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
      { to: '/admin/analytics', label: 'Admin Analytics', featureKey: 'adminAnalytics', icon: ChartNoAxesCombined, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'] },
      { to: '/admin/system', label: 'System Health', featureKey: 'adminSystem', icon: School, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
      { to: '/admin/recovery', label: 'Recovery', featureKey: 'adminRecovery', icon: History, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/admin/developer', label: 'Developer', featureKey: 'adminDeveloper', icon: Wrench, requiredAdminTypes: ['super_admin'] }
    ]
  },
  {
    key: 'overview',
    label: 'Overview',
    items: [
      { to: '/dashboard', label: 'Dashboard', featureKey: 'dashboard', icon: LayoutDashboard },
      { to: '/analytics', label: 'Analytics', featureKey: 'analytics', icon: ChartNoAxesCombined },
      { to: '/history', label: 'History', featureKey: 'history', icon: History },
      { to: '/timetable', label: 'Timetable', featureKey: 'timetable', icon: CalendarDays },
      { to: '/academic-structure', label: 'Academic Structure', featureKey: 'academicStructure', icon: Network }
    ]
  },
  {
    key: 'academics',
    label: 'Academics',
    items: [
      { to: '/students', label: 'Students', featureKey: 'students', icon: GraduationCap },
      { to: '/groups', label: 'Groups', featureKey: 'groups', icon: Users },
      { to: '/subjects', label: 'Subjects', featureKey: 'subjects', icon: BookOpen },
      { to: '/course-offerings', label: 'Course Offerings', featureKey: 'courseOfferings', icon: Library },
      { to: '/class-slots', label: 'Class Slots', featureKey: 'classSlots', icon: CalendarRange },
      { to: '/attendance-records', label: 'Attendance', featureKey: 'attendanceRecords', icon: ClipboardCheck },
      { to: '/assignments', label: 'Assignments', featureKey: 'assignments', icon: FileText },
      { to: '/submissions', label: 'Submissions', featureKey: 'submissions', icon: ClipboardCheck },
      { to: '/review-tickets', label: 'Review Tickets', featureKey: 'reviewTickets', icon: ScrollText },
      { to: '/evaluations', label: 'Evaluations', featureKey: 'evaluations', icon: CheckSquare },
      { to: '/enrollments', label: 'Enrollments', featureKey: 'enrollments', icon: UserCheck }
    ]
  },
  {
    key: 'communication',
    label: 'Communication',
    items: [
      { to: '/communication/feed', label: 'Feed', featureKey: 'communicationFeed', icon: Bell },
      { to: '/communication/announcements', label: 'Announcements', featureKey: 'communicationAnnouncements', icon: Megaphone },
      { to: '/communication/messages', label: 'Messages', featureKey: 'communicationMessages', icon: Users }
    ]
  },
  {
    key: 'clubs',
    label: 'Clubs',
    items: [
      { to: '/clubs', label: 'Clubs Hub', featureKey: 'clubs', icon: Users },
      { to: '/club-events', label: 'Club Events', featureKey: 'clubEvents', icon: CalendarDays },
      { to: '/event-registrations', label: 'Event Registrations', featureKey: 'eventRegistrations', icon: UserCheck }
    ]
  },
  {
    key: 'operations',
    label: 'Operations',
    items: [
      { to: '/audit-logs', label: 'Audit Logs', featureKey: 'auditLogs', icon: Shield },
      { to: '/developer-panel', label: 'Developer Panel', featureKey: 'developerPanel', icon: Wrench },
      { to: '/users', label: 'Users', featureKey: 'users', icon: Users }
    ]
  },
  {
    key: 'setup',
    label: 'Academic Setup',
    items: [
      { to: '/faculties', label: 'Faculties', featureKey: 'faculties', icon: Building2 },
      { to: '/departments', label: 'Departments', featureKey: 'departments', icon: Building2 },
      { to: '/programs', label: 'Programs', featureKey: 'programs', icon: Library },
      { to: '/specializations', label: 'Specializations', featureKey: 'specializations', icon: GitBranch },
      { to: '/batches', label: 'Batches', featureKey: 'batches', icon: GraduationCap },
      { to: '/semesters', label: 'Semesters', featureKey: 'semesters', icon: CalendarRange },
      { to: '/sections', label: 'Sections', featureKey: 'sections', icon: School },
      { to: '/courses', label: 'Courses', featureKey: 'courses', icon: BookOpen },
      { to: '/years', label: 'Years', featureKey: 'years', icon: GraduationCap },
      { to: '/branches', label: 'Branches', featureKey: 'branches', icon: GitBranch }
    ]
  }
];

export default function Sidebar({ user, collapsed, mobileOpen, onCloseMobile, onLogout }) {
  const location = useLocation();
  const { pushToast } = useToast();
  const role = user?.role;
  const isAdmin = role === 'admin';
  const [hasLogo, setHasLogo] = useState(false);
  const [logoVersion, setLogoVersion] = useState('');
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [openGroups, setOpenGroups] = useState({});
  const logoInputRef = useRef(null);
  const roleGroupOrder = useMemo(() => {
    if (role === 'admin') {
      return ['adminPanel', 'overview', 'academics', 'communication', 'clubs', 'operations', 'setup'];
    }
    if (role === 'teacher') {
      return ['overview', 'academics', 'communication', 'clubs', 'operations'];
    }
    return ['overview', 'academics', 'communication', 'clubs'];
  }, [role]);
  const visibleGroups = useMemo(
    () =>
      groupedItems
        .map((group) => ({
          ...group,
          items: group.items.filter((item) => {
            if (role === 'student' && item.to === '/academic-structure') {
              return false;
            }
            if (role === 'admin' && item.requiredAdminTypes?.length) {
              const currentAdminType = user?.admin_type || 'admin';
              if (!item.requiredAdminTypes.includes(currentAdminType)) {
                return false;
              }
            }
            return canAccessFeature(user, FEATURE_ACCESS[item.featureKey]);
          })
        }))
        .filter((group) => group.items.length > 0)
        .sort((a, b) => roleGroupOrder.indexOf(a.key) - roleGroupOrder.indexOf(b.key)),
    [role, roleGroupOrder, user]
  );
  const flatVisibleItems = useMemo(
    () => visibleGroups.flatMap((group) => group.items),
    [visibleGroups]
  );
  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);
  const logoUrl = hasLogo
    ? `${backendBaseUrl}/api/v1/branding/logo${logoVersion ? `?v=${encodeURIComponent(logoVersion)}` : ''}`
    : null;

  useEffect(() => {
    const next = {};
    for (const group of visibleGroups) {
      next[group.key] = group.key === 'overview';
    }
    setOpenGroups(next);
  }, [visibleGroups]);

  useEffect(() => {
    const activeGroup = visibleGroups.find((group) =>
      group.items.some((item) => location.pathname.startsWith(item.to))
    );
    if (activeGroup) {
      setOpenGroups((prev) => ({ ...prev, [activeGroup.key]: true }));
    }
  }, [location.pathname, visibleGroups]);

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
          <p className="text-xs uppercase tracking-[0.18em] text-brand-500">CAPS AI</p>
          <h1 className="text-2xl font-bold leading-tight">Control Center</h1>
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

      <p className={cn('mb-3 rounded-xl bg-slate-100 px-3 py-2 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300', collapsed && 'lg:hidden')}>
        {user?.full_name} ({user?.role})
      </p>

      <nav className="flex-1 space-y-1 overflow-y-auto">
        {collapsed ? (
          flatVisibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onCloseMobile}
              title={item.label}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition',
                  isActive
                    ? 'bg-gradient-to-r from-brand-100 to-indigo-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
                  'justify-center px-2'
                )
              }
            >
              {item.icon ? <item.icon size={16} /> : null}
            </NavLink>
          ))
        ) : (
          visibleGroups.map((group) => (
            <div key={group.key} className="space-y-1">
              <button
                type="button"
                className="flex w-full items-center justify-between rounded-lg px-2 py-1 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                onClick={() => setOpenGroups((prev) => ({ ...prev, [group.key]: !prev[group.key] }))}
              >
                <span>{group.label}</span>
                {openGroups[group.key] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
              {openGroups[group.key] ? (
                <div className="space-y-1">
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={onCloseMobile}
                      title={item.label}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition',
                          isActive
                            ? 'bg-gradient-to-r from-brand-100 to-indigo-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                        )
                      }
                    >
                      {item.icon ? <item.icon size={16} /> : null}
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              ) : null}
            </div>
          ))
        )}
      </nav>

      <button className="btn-secondary mt-4 justify-start" onClick={onLogout}>
        <LogOut size={16} /> Logout
      </button>
    </aside>
  );
}
