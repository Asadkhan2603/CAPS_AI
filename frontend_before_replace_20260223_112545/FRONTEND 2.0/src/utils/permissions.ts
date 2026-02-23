import { Role, FEATURE_ACCESS } from '../config/featureAccess';

interface User {
  role: Role;
  extended_roles?: string[];
}

export const hasPermission = (user: User | null, featureKey: string): boolean => {
  if (!user) return false;

  const access = FEATURE_ACCESS[featureKey];
  if (!access) return true; // Default to allow if not defined

  const hasRole = access.roles.includes(user.role);
  if (!hasRole) return false;

  if (user.role === 'teacher' && access.requiredTeacherExtensions) {
    const userExtensions = user.extended_roles || [];
    return access.requiredTeacherExtensions.some(ext => userExtensions.includes(ext));
  }

  return true;
};
