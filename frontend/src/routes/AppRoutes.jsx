import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import ProtectedRoute from './ProtectedRoute';
import PageSkeleton from '../components/ui/PageSkeleton';
import { FEATURE_ACCESS } from '../config/featureAccess';
import { findNavigationGroupByItemPath, getWorkspaceGroupLandingPath, getWorkspaceItemPath } from '../config/navigationGroups';
import { useAuth } from '../hooks/useAuth';
import ProfilePage from '../pages/ProfilePage';

const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const DashboardPage = lazy(() => import('../pages/DashboardPage'));
const AdminDashboardPage = lazy(() => import('../pages/Admin/AdminDashboardPage'));
const AdminGovernancePage = lazy(() => import('../pages/Admin/AdminGovernancePage'));
const AdminAnalyticsPage = lazy(() => import('../pages/Admin/AdminAnalyticsPage'));
const AdminSystemPage = lazy(() => import('../pages/Admin/AdminSystemPage'));
const AdminRecoveryPage = lazy(() => import('../pages/Admin/AdminRecoveryPage'));
const AdminDeveloperPage = lazy(() => import('../pages/Admin/AdminDeveloperPage'));
const HistoryPage = lazy(() => import('../pages/HistoryPage'));
const TimetablePage = lazy(() => import('../pages/TimetablePage'));
const AcademicStructurePage = lazy(() => import('../pages/AcademicStructurePage'));
const AnalyticsPage = lazy(() => import('../pages/AnalyticsPage'));
const ProgramsPage = lazy(() => import('../pages/ProgramsPage'));
const FacultiesPage = lazy(() => import('../pages/FacultiesPage'));
const DepartmentsPage = lazy(() => import('../pages/DepartmentsPage'));
const SpecializationsPage = lazy(() => import('../pages/SpecializationsPage'));
const BatchesPage = lazy(() => import('../pages/BatchesPage'));
const SemestersPage = lazy(() => import('../pages/SemestersPage'));
const SectionsPage = lazy(() => import('../pages/ClassesPage'));
const GroupsPage = lazy(() => import('../pages/GroupsPage'));
const StudentsPage = lazy(() => import('../pages/StudentsPage'));
const SubjectsPage = lazy(() => import('../pages/SubjectsPage'));
const CourseOfferingsPage = lazy(() => import('../pages/CourseOfferingsPage'));
const ClassSlotsPage = lazy(() => import('../pages/ClassSlotsPage'));
const AttendanceRecordsPage = lazy(() => import('../pages/AttendanceRecordsPage'));
const AssignmentsPage = lazy(() => import('../pages/AssignmentsPage'));
const SubmissionsPage = lazy(() => import('../pages/SubmissionsPage'));
const AIModulePage = lazy(() => import('../pages/AIModulePage'));
const ReviewTicketsPage = lazy(() => import('../pages/ReviewTicketsPage'));
const CommunicationFeedPage = lazy(() => import('../pages/Communication/FeedPage'));
const CommunicationAnnouncementsPage = lazy(() => import('../pages/Communication/AnnouncementsPage'));
const CommunicationMessagesPage = lazy(() => import('../pages/Communication/MessagesPage'));
const ClubsPage = lazy(() => import('../pages/ClubsPage'));
const ClubEventsPage = lazy(() => import('../pages/ClubEventsPage'));
const EventRegistrationsPage = lazy(() => import('../pages/EventRegistrationsPage'));
const NotificationsPage = lazy(() => import('../pages/NotificationsPage'));
const EvaluationsPage = lazy(() => import('../pages/EvaluationsPage'));
const EnrollmentsPage = lazy(() => import('../pages/EnrollmentsPage'));
const AuditLogsPage = lazy(() => import('../pages/AuditLogsPage'));
const DeveloperPanelPage = lazy(() => import('../pages/DeveloperPanelPage'));
const UsersPage = lazy(() => import('../pages/UsersPage'));
const EvaluateSubmissionPage = lazy(() => import('../pages/Teacher/EvaluateSubmission'));

const workspaceRouteMap = {
  '/admin/dashboard': { access: FEATURE_ACCESS.adminDashboard, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'], element: <AdminDashboardPage /> },
  '/admin/governance': { access: FEATURE_ACCESS.adminGovernance, requiredAdminTypes: ['super_admin', 'admin'], element: <AdminGovernancePage /> },
  '/admin/academic-structure': { access: FEATURE_ACCESS.adminAcademicStructure, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'], element: <Navigate to="/faculties" replace /> },
  '/admin/operations': { access: FEATURE_ACCESS.adminOperations, requiredAdminTypes: ['super_admin', 'admin'], element: <Navigate to="/students" replace /> },
  '/admin/clubs': { access: FEATURE_ACCESS.adminClubs, requiredAdminTypes: ['super_admin', 'admin'], element: <Navigate to="/clubs" replace /> },
  '/admin/communication': { access: FEATURE_ACCESS.adminCommunication, requiredAdminTypes: ['super_admin', 'admin'], element: <Navigate to="/communication/announcements" replace /> },
  '/admin/compliance': { access: FEATURE_ACCESS.adminCompliance, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'], element: <Navigate to="/audit-logs" replace /> },
  '/admin/analytics': { access: FEATURE_ACCESS.adminAnalytics, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'], element: <AdminAnalyticsPage /> },
  '/admin/system': { access: FEATURE_ACCESS.adminSystem, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'], element: <AdminSystemPage /> },
  '/admin/recovery': { access: FEATURE_ACCESS.adminRecovery, requiredAdminTypes: ['super_admin', 'admin'], element: <AdminRecoveryPage /> },
  '/admin/developer': { access: FEATURE_ACCESS.adminDeveloper, requiredAdminTypes: ['super_admin'], element: <AdminDeveloperPage /> },
  '/dashboard': { access: FEATURE_ACCESS.dashboard, element: <DashboardPage /> },
  '/analytics': { access: FEATURE_ACCESS.analytics, element: <AnalyticsPage /> },
  '/history': { access: FEATURE_ACCESS.history, element: <HistoryPage /> },
  '/timetable': { access: FEATURE_ACCESS.timetable, element: <TimetablePage /> },
  '/profile': { access: FEATURE_ACCESS.profile, element: <ProfilePage /> },
  '/academic-structure': { access: FEATURE_ACCESS.academicStructure, element: <AcademicStructurePage /> },
  '/students': { access: FEATURE_ACCESS.students, element: <StudentsPage /> },
  '/groups': { access: FEATURE_ACCESS.groups, element: <GroupsPage /> },
  '/subjects': { access: FEATURE_ACCESS.subjects, element: <SubjectsPage /> },
  '/course-offerings': { access: FEATURE_ACCESS.courseOfferings, element: <CourseOfferingsPage /> },
  '/class-slots': { access: FEATURE_ACCESS.classSlots, element: <ClassSlotsPage /> },
  '/attendance-records': { access: FEATURE_ACCESS.attendanceRecords, element: <AttendanceRecordsPage /> },
  '/assignments': { access: FEATURE_ACCESS.assignments, element: <AssignmentsPage /> },
  '/submissions': { access: FEATURE_ACCESS.submissions, element: <SubmissionsPage /> },
  '/ai-operations': { access: FEATURE_ACCESS.aiModule, element: <AIModulePage /> },
  '/review-tickets': { access: FEATURE_ACCESS.reviewTickets, element: <ReviewTicketsPage /> },
  '/evaluations': { access: FEATURE_ACCESS.evaluations, element: <EvaluationsPage /> },
  '/enrollments': { access: FEATURE_ACCESS.enrollments, element: <EnrollmentsPage /> },
  '/communication/feed': { access: FEATURE_ACCESS.communicationFeed, element: <CommunicationFeedPage /> },
  '/communication/announcements': { access: FEATURE_ACCESS.communicationAnnouncements, element: <CommunicationAnnouncementsPage /> },
  '/communication/messages': { access: FEATURE_ACCESS.communicationMessages, element: <CommunicationMessagesPage /> },
  '/notifications': { access: FEATURE_ACCESS.notifications, element: <NotificationsPage /> },
  '/clubs': { access: FEATURE_ACCESS.clubs, element: <ClubsPage /> },
  '/club-events': { access: FEATURE_ACCESS.clubEvents, element: <ClubEventsPage /> },
  '/event-registrations': { access: FEATURE_ACCESS.eventRegistrations, element: <EventRegistrationsPage /> },
  '/audit-logs': { access: FEATURE_ACCESS.auditLogs, element: <AuditLogsPage /> },
  '/developer-panel': { access: FEATURE_ACCESS.developerPanel, element: <DeveloperPanelPage /> },
  '/users': { access: FEATURE_ACCESS.users, element: <UsersPage /> },
  '/faculties': { access: FEATURE_ACCESS.faculties, element: <FacultiesPage /> },
  '/departments': { access: FEATURE_ACCESS.departments, element: <DepartmentsPage /> },
  '/programs': { access: FEATURE_ACCESS.programs, element: <ProgramsPage /> },
  '/specializations': { access: FEATURE_ACCESS.specializations, element: <SpecializationsPage /> },
  '/batches': { access: FEATURE_ACCESS.batches, element: <BatchesPage /> },
  '/semesters': { access: FEATURE_ACCESS.semesters, element: <SemestersPage /> },
  '/sections': { access: FEATURE_ACCESS.sections, element: <SectionsPage /> }
};

function WorkspaceModuleRoute() {
  const params = useParams();
  const groupKey = params.groupKey || '';
  const suffix = params['*'] || '';
  const resolvedPath = `/${suffix}`.replace(/\/+$/, '');
  const route = workspaceRouteMap[resolvedPath];
  const { user } = useAuth();

  if (!route) {
    return <Navigate to={getWorkspaceGroupLandingPath(groupKey, user)} replace />;
  }

  return (
    <ProtectedRoute {...(route.access || {})} requiredAdminTypes={route.requiredAdminTypes} allowedRoles={route.allowedRoles}>
      {route.element}
    </ProtectedRoute>
  );
}

function WorkspaceRedirect({ path }) {
  const { user } = useAuth();
  const group = findNavigationGroupByItemPath(path, user);
  if (!group) {
    const route = workspaceRouteMap[path];
    if (route) {
      return (
        <ProtectedRoute {...(route.access || {})} requiredAdminTypes={route.requiredAdminTypes} allowedRoles={route.allowedRoles}>
          {route.element}
        </ProtectedRoute>
      );
    }
    return <Navigate to={path} replace />;
  }
  return <Navigate to={getWorkspaceItemPath(group.key, path)} replace />;
}

function WorkspaceGroupRedirect() {
  const { user } = useAuth();
  const { groupKey = '' } = useParams();
  return <Navigate to={getWorkspaceGroupLandingPath(groupKey, user)} replace />;
}

function CommunicationRedirect() {
  const { user } = useAuth();
  const targetGroupKey = user?.role === 'student' ? 'notices' : 'communication';
  return <Navigate to={getWorkspaceGroupLandingPath(targetGroupKey, user)} replace />;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<WorkspaceRedirect path="/dashboard" />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminDashboard}>
                <Navigate to={getWorkspaceGroupLandingPath('adminPanel')} replace />
              </ProtectedRoute>
            }
          />
          <Route path="/admin/dashboard" element={<WorkspaceRedirect path="/admin/dashboard" />} />
          <Route path="/admin/governance" element={<WorkspaceRedirect path="/admin/governance" />} />
          <Route path="/admin/academic-structure" element={<WorkspaceRedirect path="/admin/academic-structure" />} />
          <Route path="/admin/operations" element={<WorkspaceRedirect path="/admin/operations" />} />
          <Route path="/admin/clubs" element={<WorkspaceRedirect path="/admin/clubs" />} />
          <Route path="/admin/communication" element={<WorkspaceRedirect path="/admin/communication" />} />
          <Route path="/admin/compliance" element={<WorkspaceRedirect path="/admin/compliance" />} />
          <Route path="/admin/analytics" element={<WorkspaceRedirect path="/admin/analytics" />} />
          <Route path="/admin/system" element={<WorkspaceRedirect path="/admin/system" />} />
          <Route path="/admin/recovery" element={<WorkspaceRedirect path="/admin/recovery" />} />
          <Route path="/admin/developer" element={<WorkspaceRedirect path="/admin/developer" />} />
          <Route path="/history" element={<WorkspaceRedirect path="/history" />} />
          <Route path="/timetable" element={<WorkspaceRedirect path="/timetable" />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.profile}>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route path="/analytics" element={<WorkspaceRedirect path="/analytics" />} />
          <Route path="/workspace/:groupKey" element={<WorkspaceGroupRedirect />} />
          <Route path="/workspace/:groupKey/*" element={<WorkspaceModuleRoute />} />
          <Route path="/academic-structure" element={<WorkspaceRedirect path="/academic-structure" />} />
          <Route path="/faculties" element={<WorkspaceRedirect path="/faculties" />} />
          <Route path="/courses" element={<Navigate to="/programs" replace />} />
          <Route path="/programs" element={<WorkspaceRedirect path="/programs" />} />
          <Route path="/departments" element={<WorkspaceRedirect path="/departments" />} />
          <Route path="/specializations" element={<WorkspaceRedirect path="/specializations" />} />
          <Route path="/branches" element={<Navigate to="/specializations" replace />} />
          <Route path="/batches" element={<WorkspaceRedirect path="/batches" />} />
          <Route path="/years" element={<Navigate to="/batches" replace />} />
          <Route path="/semesters" element={<WorkspaceRedirect path="/semesters" />} />
          <Route path="/sections" element={<WorkspaceRedirect path="/sections" />} />
          <Route path="/students" element={<WorkspaceRedirect path="/students" />} />
          <Route path="/groups" element={<WorkspaceRedirect path="/groups" />} />
          <Route path="/subjects" element={<WorkspaceRedirect path="/subjects" />} />
          <Route path="/course-offerings" element={<WorkspaceRedirect path="/course-offerings" />} />
          <Route path="/class-slots" element={<WorkspaceRedirect path="/class-slots" />} />
          <Route path="/attendance-records" element={<WorkspaceRedirect path="/attendance-records" />} />
          <Route path="/assignments" element={<WorkspaceRedirect path="/assignments" />} />
          <Route path="/submissions" element={<WorkspaceRedirect path="/submissions" />} />
          <Route path="/ai-operations" element={<WorkspaceRedirect path="/ai-operations" />} />
          <Route
            path="/submissions/:submissionId/evaluate"
            element={
              <ProtectedRoute allowedRoles={['admin', 'teacher']}>
                <EvaluateSubmissionPage />
              </ProtectedRoute>
            }
          />
          <Route path="/review-tickets" element={<WorkspaceRedirect path="/review-tickets" />} />
          <Route
            path="/communication"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.communicationFeed}>
                <CommunicationRedirect />
              </ProtectedRoute>
            }
          />
          <Route path="/communication/feed" element={<WorkspaceRedirect path="/communication/feed" />} />
          <Route path="/communication/announcements" element={<WorkspaceRedirect path="/communication/announcements" />} />
          <Route path="/communication/messages" element={<WorkspaceRedirect path="/communication/messages" />} />
          <Route
            path="/notices"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.notices}>
                <Navigate to="/communication/announcements" replace />
              </ProtectedRoute>
            }
          />
          <Route path="/clubs" element={<WorkspaceRedirect path="/clubs" />} />
          <Route path="/club-events" element={<WorkspaceRedirect path="/club-events" />} />
          <Route
            path="/notifications"
            element={<WorkspaceRedirect path="/notifications" />}
          />
          <Route path="/evaluations" element={<WorkspaceRedirect path="/evaluations" />} />
          <Route path="/event-registrations" element={<WorkspaceRedirect path="/event-registrations" />} />
          <Route path="/enrollments" element={<WorkspaceRedirect path="/enrollments" />} />
          <Route path="/audit-logs" element={<WorkspaceRedirect path="/audit-logs" />} />
          <Route path="/developer-panel" element={<WorkspaceRedirect path="/developer-panel" />} />
          <Route path="/users" element={<WorkspaceRedirect path="/users" />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
