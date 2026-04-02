import { apiClient } from './apiClient';

export async function fetchRbacDesign() {
  const response = await apiClient.get('/admin/rbac/design');
  return response.data || {};
}

export async function fetchRbacPermissions() {
  const response = await apiClient.get('/admin/rbac/permissions');
  return Array.isArray(response.data) ? response.data : [];
}

export async function fetchRbacRoles() {
  const response = await apiClient.get('/admin/rbac/roles');
  return Array.isArray(response.data) ? response.data : [];
}

export async function createRbacRole(payload) {
  const response = await apiClient.post('/admin/rbac/roles', payload);
  return response.data;
}

export async function updateRbacRole(roleId, payload) {
  const response = await apiClient.patch(`/admin/rbac/roles/${roleId}`, payload);
  return response.data;
}

export async function deleteRbacRole(roleId) {
  const response = await apiClient.delete(`/admin/rbac/roles/${roleId}`);
  return response.data;
}

export async function fetchAdminUsers({ includeDeleted = false } = {}) {
  const response = await apiClient.get('/admin/rbac/admins', {
    params: { include_deleted: includeDeleted }
  });
  return Array.isArray(response.data) ? response.data : [];
}

export async function fetchAdminUser(userId) {
  const response = await apiClient.get(`/admin/rbac/admins/${userId}`);
  return response.data;
}

export async function createAdminUser(payload) {
  const response = await apiClient.post('/admin/rbac/admins', payload);
  return response.data;
}

export async function updateAdminUser(userId, payload) {
  const response = await apiClient.patch(`/admin/rbac/admins/${userId}`, payload);
  return response.data;
}

export async function updateAdminUserStatus(userId, payload) {
  const response = await apiClient.patch(`/admin/rbac/admins/${userId}/status`, payload);
  return response.data;
}

export async function deleteAdminUser(userId) {
  const response = await apiClient.delete(`/admin/rbac/admins/${userId}`);
  return response.data;
}
