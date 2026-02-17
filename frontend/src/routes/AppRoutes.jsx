import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import ProtectedRoute from './ProtectedRoute';
import PageLoader from '../components/ui/PageLoader';
import { FEATURE_ACCESS } from '../config/featureAccess';

const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const DashboardPage = lazy(() => import('../pages/DashboardPage'));
const HistoryPage = lazy(() => import('../pages/HistoryPage'));
const ProfilePage = lazy(() => import('../pages/ProfilePage'));
const AcademicStructurePage = lazy(() => import('../pages/AcademicStructurePage'));
const AnalyticsPage = lazy(() => import('../pages/AnalyticsPage'));
const CoursesPage = lazy(() => import('../pages/CoursesPage'));
const DepartmentsPage = lazy(() => import('../pages/DepartmentsPage'));
const BranchesPage = lazy(() => import('../pages/BranchesPage'));
const YearsPage = lazy(() => import('../pages/YearsPage'));
const ClassesPage = lazy(() => import('../pages/ClassesPage'));
const StudentsPage = lazy(() => import('../pages/StudentsPage'));
const SubjectsPage = lazy(() => import('../pages/SubjectsPage'));
const AssignmentsPage = lazy(() => import('../pages/AssignmentsPage'));
const SubmissionsPage = lazy(() => import('../pages/SubmissionsPage'));
const ReviewTicketsPage = lazy(() => import('../pages/ReviewTicketsPage'));
const NoticesPage = lazy(() => import('../pages/NoticesPage'));
const ClubsPage = lazy(() => import('../pages/ClubsPage'));
const ClubEventsPage = lazy(() => import('../pages/ClubEventsPage'));
const NotificationsPage = lazy(() => import('../pages/NotificationsPage'));
const EvaluationsPage = lazy(() => import('../pages/EvaluationsPage'));
const EnrollmentsPage = lazy(() => import('../pages/EnrollmentsPage'));
const AuditLogsPage = lazy(() => import('../pages/AuditLogsPage'));
const DeveloperPanelPage = lazy(() => import('../pages/DeveloperPanelPage'));
const UsersPage = lazy(() => import('../pages/UsersPage'));
const EventRegistrationsPage = lazy(() => import('../pages/EventRegistrationsPage'));

export function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
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
            path="/history"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.history}>
                <HistoryPage />
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
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route
            path="/academic-structure"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.academicStructure}>
                <AcademicStructurePage />
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
            path="/departments"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.departments}>
                <DepartmentsPage />
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
            path="/years"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.years}>
                <YearsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/classes"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.classes}>
                <ClassesPage />
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
            path="/subjects"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.subjects}>
                <SubjectsPage />
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
          <Route path="/submissions" element={<SubmissionsPage />} />
          <Route
            path="/review-tickets"
            element={
              <ProtectedRoute {...FEATURE_ACCESS.reviewTickets}>
                <ReviewTicketsPage />
              </ProtectedRoute>
            }
          />
          <Route path="/notices" element={<NoticesPage />} />
          <Route path="/clubs" element={<ClubsPage />} />
          <Route path="/club-events" element={<ClubEventsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/evaluations" element={<EvaluationsPage />} />
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
