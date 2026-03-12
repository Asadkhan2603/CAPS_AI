import {
  Bell,
  BookOpen,
  Building2,
  CalendarDays,
  CalendarRange,
  ChartNoAxesCombined,
  CheckSquare,
  ClipboardCheck,
  FileText,
  GitBranch,
  GraduationCap,
  History,
  LayoutDashboard,
  Library,
  Megaphone,
  Network,
  School,
  ScrollText,
  Shield,
  Sparkles,
  UserCheck,
  Users,
  Wrench
} from 'lucide-react';
import { FEATURE_ACCESS } from './featureAccess';
import { canAccessFeature } from '../utils/permissions';

const adminTeacherNavigationGroups = [
  {
    key: 'adminPanel',
    label: 'Admin Panel',
    items: [
      { to: '/admin/dashboard', label: 'Admin Dashboard', featureKey: 'adminDashboard', icon: LayoutDashboard, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'] },
      { to: '/admin/governance', label: 'Governance', featureKey: 'adminGovernance', icon: Shield, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/faculties', label: 'Academic Structure', featureKey: 'adminAcademicStructure', icon: Network, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'] },
      { to: '/students', label: 'Operations', featureKey: 'adminOperations', icon: Wrench, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/clubs', label: 'Clubs', featureKey: 'adminClubs', icon: Users, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/communication/announcements', label: 'Communication', featureKey: 'adminCommunication', icon: Megaphone, requiredAdminTypes: ['super_admin', 'admin'] },
      { to: '/audit-logs', label: 'Compliance', featureKey: 'adminCompliance', icon: Shield, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
      { to: '/admin/analytics', label: 'Admin Analytics', featureKey: 'adminAnalytics', icon: ChartNoAxesCombined, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'] },
      { to: '/admin/system', label: 'System Health', featureKey: 'adminSystem', icon: School, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
      { to: '/admin/observability', label: 'Observability', featureKey: 'adminSystem', icon: ChartNoAxesCombined, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'] },
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
      { to: '/ai-operations', label: 'AI Operations', featureKey: 'aiModule', icon: Sparkles },
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
      { to: '/sections', label: 'Sections', featureKey: 'sections', icon: School }
    ]
  },
  {
    key: 'profile',
    label: 'Profile',
    items: [
      { to: '/profile', label: 'My Profile', featureKey: 'profile', icon: UserCheck }
    ]
  }
];

const studentNavigationGroups = [
  {
    key: 'home',
    label: 'Home',
    items: [
      { to: '/dashboard', label: 'Dashboard', featureKey: 'dashboard', icon: LayoutDashboard },
      { to: '/timetable', label: 'Timetable', featureKey: 'timetable', icon: CalendarDays },
      { to: '/history', label: 'History', featureKey: 'history', icon: History }
    ]
  },
  {
    key: 'academics',
    label: 'Academics',
    items: [
      { to: '/class-slots', label: 'My Classes', featureKey: 'classSlots', icon: CalendarRange },
      { to: '/submissions', label: 'My Submissions', featureKey: 'submissions', icon: FileText },
      { to: '/evaluations', label: 'My Evaluations', featureKey: 'evaluations', icon: CheckSquare },
      { to: '/attendance-records', label: 'Attendance', featureKey: 'attendanceRecords', icon: ClipboardCheck }
    ]
  },
  {
    key: 'notices',
    label: 'Notices',
    items: [
      { to: '/communication/announcements', label: 'Announcements', featureKey: 'communicationAnnouncements', icon: Megaphone },
      { to: '/notifications', label: 'Notifications', featureKey: 'notifications', icon: Bell },
      { to: '/communication/feed', label: 'Updates', featureKey: 'communicationFeed', icon: Bell }
    ]
  },
  {
    key: 'clubs',
    label: 'Clubs',
    items: [
      { to: '/clubs', label: 'Clubs Hub', featureKey: 'clubs', icon: Users },
      { to: '/club-events', label: 'Club Events', featureKey: 'clubEvents', icon: CalendarDays },
      { to: '/event-registrations', label: 'Registrations', featureKey: 'eventRegistrations', icon: UserCheck }
    ]
  },
  {
    key: 'profile',
    label: 'Profile',
    items: [
      { to: '/profile', label: 'My Profile', featureKey: 'profile', icon: UserCheck }
    ]
  }
];

function getNavigationGroupsForRole(role) {
  if (role === 'student') {
    return studentNavigationGroups;
  }
  return adminTeacherNavigationGroups;
}

export function getRoleGroupOrder(role) {
  if (role === 'admin') {
    return ['adminPanel', 'overview', 'academics', 'communication', 'clubs', 'operations', 'setup', 'profile'];
  }
  if (role === 'teacher') {
    return ['overview', 'academics', 'communication', 'clubs', 'operations', 'profile'];
  }
  return ['home', 'academics', 'notices', 'clubs', 'profile'];
}

export function getVisibleNavigationGroups(user) {
  const role = user?.role;
  const roleGroupOrder = getRoleGroupOrder(role);
  const groups = getNavigationGroupsForRole(role);

  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
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
    .sort((a, b) => roleGroupOrder.indexOf(a.key) - roleGroupOrder.indexOf(b.key));
}

export function getWorkspaceGroupPath(groupKey) {
  return `/workspace/${groupKey}`;
}

export function getWorkspaceItemPath(groupKey, itemPath) {
  return `${getWorkspaceGroupPath(groupKey)}${itemPath}`;
}

export function findNavigationGroupByItemPath(itemPath, user) {
  const groups = user ? getVisibleNavigationGroups(user) : [...studentNavigationGroups, ...adminTeacherNavigationGroups];
  return groups.find((group) => group.items.some((item) => item.to === itemPath)) || null;
}

export function getWorkspaceGroupLandingPath(groupKey, user) {
  const groups = user ? getVisibleNavigationGroups(user) : [...studentNavigationGroups, ...adminTeacherNavigationGroups];
  const group = groups.find((item) => item.key === groupKey) || null;
  const firstItem = group?.items?.[0] || null;
  return firstItem ? getWorkspaceItemPath(group.key, firstItem.to) : '/dashboard';
}

export function getWorkspaceHomeItemPath(user) {
  const homeGroup = findNavigationGroupByItemPath('/dashboard', user);
  return getWorkspaceItemPath(homeGroup?.key || 'overview', '/dashboard');
}
