import { Suspense } from 'react';
import { lazyWithRetry } from '../utils/lazyWithRetry';
import { Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import ProtectedRoute from './ProtectedRoute';
import PageSkeleton from '../components/ui/PageSkeleton';
import { FEATURE_ACCESS } from '../config/featureAccess';
import { findNavigationGroupByItemPath, getWorkspaceGroupLandingPath, getWorkspaceItemPath } from '../config/navigationGroups';
import { useAuth } from '../hooks/useAuth';
import ProfilePage from '../pages/ProfilePage';

const LoginPage = lazyWithRetry(() => import('../pages/LoginPage'));
const RegisterPage = lazyWithRetry(() => import('../pages/RegisterPage'));
const DashboardPage = lazyWithRetry(() => import('../pages/DashboardPage'));
const AdminDashboardPage = lazyWithRetry(() => import('../pages/Admin/AdminDashboardPage'));
const AdminOnboardingPage = lazyWithRetry(() => import('../pages/Admin/AdminOnboardingPage'));
const AdminRbacPage = lazyWithRetry(() => import('../pages/Admin/AdminRbacPage'));
const AdminGovernancePage = lazyWithRetry(() => import('../pages/Admin/AdminGovernancePage'));
const AdminAnalyticsPage = lazyWithRetry(() => import('../pages/Admin/AdminAnalyticsPage'));
const AdminSystemPage = lazyWithRetry(() => import('../pages/Admin/AdminSystemPage'));
const AdminObservabilityPage = lazyWithRetry(() => import('../pages/Admin/AdminObservabilityPage'));
const AdminRecoveryPage = lazyWithRetry(() => import('../pages/Admin/AdminRecoveryPage'));
const AdminDeveloperPage = lazyWithRetry(() => import('../pages/Admin/AdminDeveloperPage'));
const HistoryPage = lazyWithRetry(() => import('../pages/HistoryPage'));
const TimetablePage = lazyWithRetry(() => import('../pages/TimetablePage'));
const AcademicStructurePage = lazyWithRetry(() => import('../pages/AcademicStructurePage'));
const AnalyticsPage = lazyWithRetry(() => import('../pages/AnalyticsPage'));
const ProgramsPage = lazyWithRetry(() => import('../pages/ProgramsPage'));
const UniversitiesPage = lazyWithRetry(() => import('../pages/UniversitiesPage'));
const FacultiesPage = lazyWithRetry(() => import('../pages/FacultiesPage'));
const DepartmentsPage = lazyWithRetry(() => import('../pages/DepartmentsPage'));
const SpecializationsPage = lazyWithRetry(() => import('../pages/SpecializationsPage'));
const BatchesPage = lazyWithRetry(() => import('../pages/BatchesPage'));
const SemestersPage = lazyWithRetry(() => import('../pages/SemestersPage'));
const SectionsPage = lazyWithRetry(() => import('../pages/ClassesPage'));
const GroupsPage = lazyWithRetry(() => import('../pages/GroupsPage'));
const StudentsPage = lazyWithRetry(() => import('../pages/StudentsPage'));
const StudentBulkImportPage = lazyWithRetry(() => import('../pages/StudentBulkImportPage'));
const SubjectsPage = lazyWithRetry(() => import('../pages/SubjectsPage'));
const CourseOfferingsPage = lazyWithRetry(() => import('../pages/CourseOfferingsPage'));
const ClassSlotsPage = lazyWithRetry(() => import('../pages/ClassSlotsPage'));
const AttendanceRecordsPage = lazyWithRetry(() => import('../pages/AttendanceRecordsPage'));
const AssignmentsPage = lazyWithRetry(() => import('../pages/AssignmentsPage'));
const SubmissionsPage = lazyWithRetry(() => import('../pages/SubmissionsPage'));
const AIModulePage = lazyWithRetry(() => import('../pages/AIModulePage'));
const ReviewTicketsPage = lazyWithRetry(() => import('../pages/ReviewTicketsPage'));
const ExamsPage = lazyWithRetry(() => import('../pages/ExamsPage'));
const GrievancesPage = lazyWithRetry(() => import('../pages/GrievancesPage'));
const CommunicationFeedPage = lazyWithRetry(() => import('../pages/Communication/FeedPage'));
const CommunicationAnnouncementsPage = lazyWithRetry(() => import('../pages/Communication/AnnouncementsPage'));
const CommunicationMessagesPage = lazyWithRetry(() => import('../pages/Communication/MessagesPage'));
const ClubsPage = lazyWithRetry(() => import('../pages/ClubsPage'));
const ClubEventsPage = lazyWithRetry(() => import('../pages/ClubEventsPage'));
const EventRegistrationsPage = lazyWithRetry(() => import('../pages/EventRegistrationsPage'));
const NotificationsPage = lazyWithRetry(() => import('../pages/NotificationsPage'));
const EvaluationsPage = lazyWithRetry(() => import('../pages/EvaluationsPage'));
const EnrollmentsPage = lazyWithRetry(() => import('../pages/EnrollmentsPage'));
const CoordinatorStudentMappingPage = lazyWithRetry(() => import('../pages/CoordinatorStudentMappingPage'));
const AuditLogsPage = lazyWithRetry(() => import('../pages/AuditLogsPage'));
const DeveloperPanelPage = lazyWithRetry(() => import('../pages/DeveloperPanelPage'));
const UsersPage = lazyWithRetry(() => import('../pages/UsersPage'));
const HelpSupportPage = lazyWithRetry(() => import('../pages/HelpSupportPage'));
const EvaluateSubmissionPage = lazyWithRetry(() => import('../pages/Teacher/EvaluateSubmission'));

const workspaceRouteMap = {
  '/admin/dashboard': { access: FEATURE_ACCESS.adminDashboard, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'], element: <AdminDashboardPage /> },
  '/admin/onboarding': { access: FEATURE_ACCESS.adminOnboarding, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'], element: <AdminOnboardingPage /> },
  '/admin/rbac': { access: FEATURE_ACCESS.adminRbac, requiredAdminTypes: ['super_admin'], element: <AdminRbacPage /> },
  '/admin/governance': { access: FEATURE_ACCESS.adminGovernance, requiredAdminTypes: ['super_admin', 'admin'], element: <AdminGovernancePage /> },
  '/admin/academic-structure': { access: FEATURE_ACCESS.adminAcademicStructure, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'], element: <Navigate to="/academic-structure" replace /> },
  '/admin/operations': { access: FEATURE_ACCESS.adminOperations, requiredAdminTypes: ['super_admin', 'admin'], element: <Navigate to="/students" replace /> },
  '/admin/clubs': { access: FEATURE_ACCESS.adminClubs, requiredAdminTypes: ['super_admin', 'admin'], element: <Navigate to="/clubs" replace /> },
  '/admin/communication': { access: FEATURE_ACCESS.adminCommunication, requiredAdminTypes: ['super_admin', 'admin'], element: <Navigate to="/communication/announcements" replace /> },
  '/admin/compliance': { access: FEATURE_ACCESS.adminCompliance, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'], element: <Navigate to="/audit-logs" replace /> },
  '/admin/analytics': { access: FEATURE_ACCESS.adminAnalytics, requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'compliance_admin'], element: <AdminAnalyticsPage /> },
  '/admin/system': { access: FEATURE_ACCESS.adminSystem, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'], element: <AdminSystemPage /> },
  '/admin/observability': { access: FEATURE_ACCESS.adminSystem, requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin'], element: <AdminObservabilityPage /> },
  '/admin/recovery': { access: FEATURE_ACCESS.adminRecovery, requiredAdminTypes: ['super_admin', 'admin'], element: <AdminRecoveryPage /> },
  '/admin/developer': { access: FEATURE_ACCESS.adminDeveloper, requiredAdminTypes: ['super_admin'], element: <AdminDeveloperPage /> },
  '/dashboard': { access: FEATURE_ACCESS.dashboard, element: <DashboardPage /> },
  '/analytics': { access: FEATURE_ACCESS.analytics, element: <AnalyticsPage /> },
  '/history': { access: FEATURE_ACCESS.history, element: <HistoryPage /> },
  '/timetable': { access: FEATURE_ACCESS.timetable, element: <TimetablePage /> },
  '/profile': { access: FEATURE_ACCESS.profile, element: <ProfilePage /> },
  '/help': { access: FEATURE_ACCESS.helpSupport, element: <HelpSupportPage /> },
  '/academic-structure': { access: FEATURE_ACCESS.academicStructure, element: <AcademicStructurePage /> },
  '/students': { access: FEATURE_ACCESS.students, element: <StudentsPage /> },
  '/students/bulk-import': { access: FEATURE_ACCESS.studentBulkImport, element: <StudentBulkImportPage /> },
  '/students/section-mapping': { access: FEATURE_ACCESS.coordinatorStudentMapping, element: <CoordinatorStudentMappingPage /> },
  '/groups': { access: FEATURE_ACCESS.groups, element: <GroupsPage /> },
  '/subjects': { access: FEATURE_ACCESS.subjects, element: <SubjectsPage /> },
  '/course-offerings': { access: FEATURE_ACCESS.courseOfferings, element: <CourseOfferingsPage /> },
  '/class-slots': { access: FEATURE_ACCESS.classSlots, element: <ClassSlotsPage /> },
  '/attendance-records': { access: FEATURE_ACCESS.attendanceRecords, element: <AttendanceRecordsPage /> },
  '/assignments': { access: FEATURE_ACCESS.assignments, element: <AssignmentsPage /> },
  '/submissions': { access: FEATURE_ACCESS.submissions, element: <SubmissionsPage /> },
  '/ai-operations': { access: FEATURE_ACCESS.aiModule, element: <AIModulePage /> },
  '/review-tickets': { access: FEATURE_ACCESS.reviewTickets, element: <ReviewTicketsPage /> },
  '/exams': { access: FEATURE_ACCESS.exams, element: <ExamsPage /> },
  '/grievances': { access: FEATURE_ACCESS.grievancesStudent, element: <GrievancesPage mode="student" /> },
  '/grievances/coordinator': { access: FEATURE_ACCESS.grievancesCoordinator, element: <GrievancesPage mode="coordinator" /> },
  '/grievances/hod': { access: FEATURE_ACCESS.grievancesHod, element: <GrievancesPage mode="hod" /> },
  '/grievances/dean': { access: FEATURE_ACCESS.grievancesDean, element: <GrievancesPage mode="dean" /> },
  '/grievances/assigned': { access: FEATURE_ACCESS.grievancesAssigned, element: <GrievancesPage mode="assigned" /> },
  '/grievances/fallback': { access: FEATURE_ACCESS.grievancesFallback, element: <GrievancesPage mode="fallback" /> },
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
  '/universities': { access: FEATURE_ACCESS.universities, element: <UniversitiesPage /> },
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
  const location = useLocation();
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
  return <Navigate to={{ pathname: getWorkspaceItemPath(group.key, path), search: location.search, hash: location.hash }} replace />;
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
          <Route path="/admin/onboarding" element={<WorkspaceRedirect path="/admin/onboarding" />} />
          <Route path="/admin/rbac" element={<WorkspaceRedirect path="/admin/rbac" />} />
          <Route path="/admin/governance" element={<WorkspaceRedirect path="/admin/governance" />} />
          <Route path="/admin/academic-structure" element={<WorkspaceRedirect path="/admin/academic-structure" />} />
          <Route path="/admin/operations" element={<WorkspaceRedirect path="/admin/operations" />} />
          <Route path="/admin/clubs" element={<WorkspaceRedirect path="/admin/clubs" />} />
          <Route path="/admin/communication" element={<WorkspaceRedirect path="/admin/communication" />} />
          <Route path="/admin/compliance" element={<WorkspaceRedirect path="/admin/compliance" />} />
          <Route path="/admin/analytics" element={<WorkspaceRedirect path="/admin/analytics" />} />
          <Route path="/admin/system" element={<WorkspaceRedirect path="/admin/system" />} />
          <Route path="/admin/observability" element={<WorkspaceRedirect path="/admin/observability" />} />
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
          <Route path="/help" element={<WorkspaceRedirect path="/help" />} />
          <Route path="/analytics" element={<WorkspaceRedirect path="/analytics" />} />
          <Route path="/workspace/:groupKey" element={<WorkspaceGroupRedirect />} />
          <Route path="/workspace/:groupKey/*" element={<WorkspaceModuleRoute />} />
          <Route path="/academic-structure" element={<WorkspaceRedirect path="/academic-structure" />} />
          <Route path="/faculties" element={<WorkspaceRedirect path="/faculties" />} />
          <Route path="/universities" element={<WorkspaceRedirect path="/universities" />} />
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
          <Route path="/students/bulk-import" element={<WorkspaceRedirect path="/students/bulk-import" />} />
          <Route path="/students/section-mapping" element={<WorkspaceRedirect path="/students/section-mapping" />} />
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
          <Route path="/grievances" element={<WorkspaceRedirect path="/grievances" />} />
          <Route path="/grievances/coordinator" element={<WorkspaceRedirect path="/grievances/coordinator" />} />
          <Route path="/grievances/hod" element={<WorkspaceRedirect path="/grievances/hod" />} />
          <Route path="/grievances/dean" element={<WorkspaceRedirect path="/grievances/dean" />} />
          <Route path="/grievances/assigned" element={<WorkspaceRedirect path="/grievances/assigned" />} />
          <Route path="/grievances/fallback" element={<WorkspaceRedirect path="/grievances/fallback" />} />
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
          <Route path="/exams" element={<WorkspaceRedirect path="/exams" />} />
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

