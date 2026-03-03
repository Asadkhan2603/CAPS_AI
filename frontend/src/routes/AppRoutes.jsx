import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import ProtectedRoute from './ProtectedRoute';
import PageSkeleton from '../components/ui/PageSkeleton';
import { FEATURE_ACCESS } from '../config/featureAccess';

const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const DashboardPage = lazy(() => import('../pages/DashboardPage'));
const AdminDashboardPage = lazy(() => import('../pages/Admin/AdminDashboardPage'));
const AdminGovernancePage = lazy(() => import('../pages/Admin/AdminGovernancePage'));
const AdminAcademicStructurePage = lazy(() => import('../pages/Admin/AdminAcademicStructurePage'));
const AdminOperationsPage = lazy(() => import('../pages/Admin/AdminOperationsPage'));
const AdminClubsPage = lazy(() => import('../pages/Admin/AdminClubsPage'));
const AdminCommunicationPage = lazy(() => import('../pages/Admin/AdminCommunicationPage'));
const AdminCompliancePage = lazy(() => import('../pages/Admin/AdminCompliancePage'));
const AdminAnalyticsPage = lazy(() => import('../pages/Admin/AdminAnalyticsPage'));
const AdminSystemPage = lazy(() => import('../pages/Admin/AdminSystemPage'));
const AdminRecoveryPage = lazy(() => import('../pages/Admin/AdminRecoveryPage'));
const AdminDeveloperPage = lazy(() => import('../pages/Admin/AdminDeveloperPage'));
const HistoryPage = lazy(() => import('../pages/HistoryPage'));
const TimetablePage = lazy(() => import('../pages/TimetablePage'));
const ProfilePage = lazy(() => import('../pages/ProfilePage'));
const AcademicStructurePage = lazy(() => import('../pages/AcademicStructurePage'));
const AnalyticsPage = lazy(() => import('../pages/AnalyticsPage'));
const CoursesPage = lazy(() => import('../pages/CoursesPage'));
const ProgramsPage = lazy(() => import('../pages/ProgramsPage'));
const FacultiesPage = lazy(() => import('../pages/FacultiesPage'));
const DepartmentsPage = lazy(() => import('../pages/DepartmentsPage'));
const SpecializationsPage = lazy(() => import('../pages/SpecializationsPage'));
const BranchesPage = lazy(() => import('../pages/BranchesPage'));
const BatchesPage = lazy(() => import('../pages/BatchesPage'));
const YearsPage = lazy(() => import('../pages/YearsPage'));
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
const ReviewTicketsPage = lazy(() => import('../pages/ReviewTicketsPage'));
const CommunicationFeedPage = lazy(() => import('../pages/Communication/FeedPage'));
const CommunicationAnnouncementsPage = lazy(() => import('../pages/Communication/AnnouncementsPage'));
const CommunicationMessagesPage = lazy(() => import('../pages/Communication/MessagesPage'));
const NoticesPage = lazy(() => import('../pages/NoticesPage'));
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
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminDashboard}>
                <Navigate to="/admin/dashboard" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminDashboard} requiredAdminTypes={['super_admin', 'admin', 'academic_admin', 'compliance_admin']}>
                <AdminDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/governance"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminGovernance} requiredAdminTypes={['super_admin', 'admin']}>
                <AdminGovernancePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/academic-structure"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminAcademicStructure} requiredAdminTypes={['super_admin', 'admin', 'academic_admin']}>
                <AdminAcademicStructurePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/operations"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminOperations} requiredAdminTypes={['super_admin', 'admin']}>
                <AdminOperationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/clubs"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminClubs} requiredAdminTypes={['super_admin', 'admin']}>
                <AdminClubsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/communication"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminCommunication} requiredAdminTypes={['super_admin', 'admin']}>
                <AdminCommunicationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/compliance"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminCompliance} requiredAdminTypes={['super_admin', 'admin', 'compliance_admin']}>
                <AdminCompliancePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/analytics"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminAnalytics} requiredAdminTypes={['super_admin', 'admin', 'academic_admin', 'compliance_admin']}>
                <AdminAnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/system"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminSystem} requiredAdminTypes={['super_admin', 'admin', 'compliance_admin']}>
                <AdminSystemPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/recovery"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminRecovery} requiredAdminTypes={['super_admin', 'admin']}>
                <AdminRecoveryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/developer"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.adminDeveloper} requiredAdminTypes={['super_admin']}>
                <AdminDeveloperPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.history}>
                <HistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/timetable"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.timetable}>
                <TimetablePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.profile}>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.analytics}>
                <AnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/academic-structure"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.academicStructure}>
                <AcademicStructurePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/faculties"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.faculties}>
                <FacultiesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.courses}>
                <CoursesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/programs"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.programs}>
                <ProgramsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/departments"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.departments}>
                <DepartmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/specializations"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.specializations}>
                <SpecializationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/branches"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.branches}>
                <BranchesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/batches"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.batches}>
                <BatchesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/years"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.years}>
                <YearsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/semesters"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.semesters}>
                <SemestersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sections"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.sections}>
                <SectionsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/students"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.students}>
                <StudentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.groups}>
                <GroupsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/subjects"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.subjects}>
                <SubjectsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/course-offerings"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.courseOfferings}>
                <CourseOfferingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/class-slots"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.classSlots}>
                <ClassSlotsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/attendance-records"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.attendanceRecords}>
                <AttendanceRecordsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assignments"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.assignments}>
                <AssignmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/submissions"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.submissions}>
                <SubmissionsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/submissions/:submissionId/evaluate"
            element={
              <ProtectedRoute allowedRoles={['admin', 'teacher']}>
                <EvaluateSubmissionPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/review-tickets"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.reviewTickets}>
                <ReviewTicketsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/communication"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.communicationFeed}>
                <Navigate to="/communication/feed" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/communication/feed"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.communicationFeed}>
                <CommunicationFeedPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/communication/announcements"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.communicationAnnouncements}>
                <CommunicationAnnouncementsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/communication/messages"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.communicationMessages}>
                <CommunicationMessagesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notices"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.notices}>
                <NoticesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clubs"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.clubs}>
                <ClubsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/club-events"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.clubEvents}>
                <ClubEventsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.notifications}>
                <NotificationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluations"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.evaluations}>
                <EvaluationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/event-registrations"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.eventRegistrations}>
                <EventRegistrationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/enrollments"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.enrollments}>
                <EnrollmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit-logs"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.auditLogs}>
                <AuditLogsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/developer-panel"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.developerPanel}>
                <DeveloperPanelPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.users}>
                <UsersPage />
              </ProtectedRoute>
            }
          />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
