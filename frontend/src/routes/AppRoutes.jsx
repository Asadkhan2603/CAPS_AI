import { Navigate, Route, Routes } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import ProtectedRoute from './ProtectedRoute';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import DashboardPage from '../pages/DashboardPage';
import CoursesPage from '../pages/CoursesPage';
import YearsPage from '../pages/YearsPage';
import ClassesPage from '../pages/ClassesPage';
import SectionsPage from '../pages/SectionsPage';
import SectionSubjectsPage from '../pages/SectionSubjectsPage';
import StudentsPage from '../pages/StudentsPage';
import SubjectsPage from '../pages/SubjectsPage';
import AssignmentsPage from '../pages/AssignmentsPage';
import SubmissionsPage from '../pages/SubmissionsPage';

export function AppRoutes() {
  return (
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
          path="/courses"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <CoursesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/years"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <YearsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/classes"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <ClassesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sections"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <SectionsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/section-subjects"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <SectionSubjectsPage />
            </ProtectedRoute>
          }
        />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/subjects" element={<SubjectsPage />} />
        <Route path="/assignments" element={<AssignmentsPage />} />
        <Route path="/submissions" element={<SubmissionsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
