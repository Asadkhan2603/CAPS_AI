import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import PageLoader from '../components/ui/PageLoader';
import { canAccessFeature } from '../utils/permissions';

export default function ProtectedRoute({
  children,
  allowedRoles = null,
  requiredTeacherExtensions = null,
  requiredAdminTypes = null
}) {
  const { isAuthenticated, checking, user } = useAuth();

  if (checking) {
    return <PageLoader label="Checking session..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const hasAccess = canAccessFeature(user, {
    allowedRoles: allowedRoles || [],
    requiredTeacherExtensions: requiredTeacherExtensions || [],
    requiredAdminTypes: requiredAdminTypes || []
  });

  if (!hasAccess) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
