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
  const { allowedRoles = [], requiredTeacherExtensions = [], requiredAdminTypes = [] } = options;
  if (!(hasRole(user, allowedRoles) && hasAnyTeacherExtension(user, requiredTeacherExtensions))) {
    return false;
  }
  if (requiredAdminTypes.length > 0 && user?.role === 'admin') {
    const adminType = user?.admin_type || 'admin';
    return requiredAdminTypes.includes(adminType);
  }
  return true;
}
