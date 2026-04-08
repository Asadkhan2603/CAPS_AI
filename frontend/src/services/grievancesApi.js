import { apiClient } from './apiClient';

export async function listMyGrievances(params = {}) {
  const response = await apiClient.get('/grievances/mine', { params });
  return response.data || [];
}

export async function listGrievanceInbox(params = {}) {
  const response = await apiClient.get('/grievances/inbox', { params });
  return response.data || [];
}

export async function getGrievance(grievanceId) {
  const response = await apiClient.get(`/grievances/${grievanceId}`);
  return response.data;
}

export async function listGrievanceForwardTargets(query = '') {
  const response = await apiClient.get('/grievances/forward-targets', {
    params: query ? { q: query } : undefined
  });
  return response.data || [];
}

export async function createGrievance({ category, title, description, attachment }) {
  const formData = new FormData();
  formData.append('category', category);
  formData.append('title', title);
  formData.append('description', description);
  if (attachment) {
    formData.append('attachment', attachment);
  }
  const response = await apiClient.post('/grievances/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

export async function addGrievanceComment(grievanceId, message) {
  const response = await apiClient.post(`/grievances/${grievanceId}/comments`, { message });
  return response.data;
}

export async function addGrievanceInternalNote(grievanceId, message) {
  const response = await apiClient.post(`/grievances/${grievanceId}/internal-notes`, { message });
  return response.data;
}

export async function forwardGrievance(grievanceId, targetUserId, note) {
  const response = await apiClient.post(`/grievances/${grievanceId}/forward`, {
    target_user_id: targetUserId,
    note
  });
  return response.data;
}

export async function updateGrievanceStatus(grievanceId, status, resolutionNote = '') {
  const response = await apiClient.patch(`/grievances/${grievanceId}/status`, {
    status,
    resolution_note: resolutionNote || null
  });
  return response.data;
}

export async function reopenGrievance(grievanceId, message = '') {
  const response = await apiClient.post(`/grievances/${grievanceId}/reopen`, {
    message: message || null
  });
  return response.data;
}
