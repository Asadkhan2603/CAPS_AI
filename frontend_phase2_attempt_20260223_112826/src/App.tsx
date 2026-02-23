import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { AcademicStructurePage } from './pages/AcademicStructurePage';
import { ProfilePage } from './pages/ProfilePage';
import { AssignmentsPage } from './pages/AssignmentsPage';
import { EvaluateSubmissionPage } from './pages/EvaluateSubmissionPage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<Navigate to="/login" replace />} />
          
          <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<ProtectedRoute featureKey="DASHBOARD"><DashboardPage /></ProtectedRoute>} />
            <Route path="/academic-structure" element={<ProtectedRoute featureKey="ACADEMIC_STRUCTURE"><AcademicStructurePage /></ProtectedRoute>} />
            <Route path="/assignments" element={<ProtectedRoute featureKey="ASSIGNMENTS"><AssignmentsPage /></ProtectedRoute>} />
            <Route path="/submissions/:submissionId/evaluate" element={<ProtectedRoute allowedRoles={['admin', 'teacher']}><EvaluateSubmissionPage /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute featureKey="PROFILE"><ProfilePage /></ProtectedRoute>} />
             
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
