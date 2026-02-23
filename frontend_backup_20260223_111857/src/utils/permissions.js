export function hasRole(user, allowedRoles = []) {
  if (!user || allowedRoles.length === 0) {
    return true;
  }
  return allowedRoles.includes(user.role);
}

export function hasAnyTeacherExtension(user, requiredExtensions = []) {
  if (!user || requiredExtensions.length === 0) {
    return true;
  }
  if (user.role !== 'teacher') {
    return true;
  }
  const userExtensions = user.extended_roles || [];
  return requiredExtensions.some((ext) => userExtensions.includes(ext));
}

export function canAccessFeature(user, options = {}) {
  const { allowedRoles = [], requiredTeacherExtensions = [] } = options;
  return hasRole(user, allowedRoles) && hasAnyTeacherExtension(user, requiredTeacherExtensions);
}
