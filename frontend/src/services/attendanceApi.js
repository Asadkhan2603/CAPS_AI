import { apiClient } from './apiClient';

export async function getAttendanceMarkingLookups() {
  const response = await apiClient.get('/attendance-records/marking-lookups');
  return response.data?.items || [];
}

export async function getAttendanceRoster(classSlotId) {
  const response = await apiClient.get(`/attendance-records/roster/${classSlotId}`);
  return response.data;
}

export async function markAttendanceBulk(payload) {
  const response = await apiClient.post('/attendance-records/mark-bulk', payload);
  return response.data || [];
}

export async function getAttendanceSectionSummary(sectionId, params = {}) {
  const response = await apiClient.get('/attendance-records/summary', {
    params: { section_id: sectionId, ...params }
  });
  return response.data;
}

export async function getMyAttendanceSummary(params = {}) {
  const response = await apiClient.get('/attendance-records/my-summary', { params });
  return response.data;
}

export async function getAttendanceAnalytics(sectionId, params = {}) {
  const response = await apiClient.get('/attendance-records/analytics', {
    params: { section_id: sectionId, ...params }
  });
  return response.data;
}

export async function getMyAttendanceAnalytics(params = {}) {
  const response = await apiClient.get('/attendance-records/my-analytics', { params });
  return response.data;
}
