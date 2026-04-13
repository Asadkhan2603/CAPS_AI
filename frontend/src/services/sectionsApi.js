import { apiClient } from './apiClient';

export async function getSections(params = {}) {
  return await apiClient.get('/sections/', { params });
}

export async function createSection(payload) {
  return await apiClient.post('/sections/', payload);
}

export async function getSectionPage(params = {}, pageSize = 100) {
  const response = await apiClient.get('/sections/', {
    params: {
      ...params,
      skip: params.skip ?? 0,
      limit: params.limit ?? pageSize
    }
  });
  return Array.isArray(response.data) ? response.data : [];
}

export async function getTeacherSectionsAnalytics() {
  return await apiClient.get('/analytics/teacher/sections');
}

export async function getSectionDashboard(params = {}) {
  const response = await apiClient.get('/sections/dashboard', { params });
  return response.data;
}

export async function lockSectionMapping(sectionId, reason = '') {
  return await apiClient.post(`/sections/${sectionId}/lock`, { reason });
}

export async function unlockSectionMapping(sectionId, reason = '') {
  return await apiClient.post(`/sections/${sectionId}/unlock`, { reason });
}
