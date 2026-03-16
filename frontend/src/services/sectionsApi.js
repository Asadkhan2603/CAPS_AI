import { apiClient } from './apiClient';
import { listAllPages } from './paginatedLookups';

export async function getSections(params = {}) {
  return await apiClient.get('/sections/', { params });
}

export async function createSection(payload) {
  return await apiClient.post('/sections/', payload);
}

export async function getAllSections(pageSize = 100) {
  return listAllPages('/sections/', {}, pageSize);
}

export async function getTeacherSectionsAnalytics() {
  return await apiClient.get('/analytics/teacher/sections');
}
