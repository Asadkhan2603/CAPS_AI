import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import AssignmentsPage from "../pages/AssignmentsPage";
import DashboardPage from "../pages/DashboardPage";
import StudentsPage from "../pages/StudentsPage";
import SubjectsPage from "../pages/SubjectsPage";

export function AppRoutes() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/subjects" element={<SubjectsPage />} />
        <Route path="/assignments" element={<AssignmentsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppLayout>
  );
}
