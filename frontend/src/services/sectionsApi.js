import { apiClient } from './apiClient';

export async function getSections(params = {}) {
  return await apiClient.get('/sections/', { params });
}

export async function createSection(payload) {
  return await apiClient.post('/sections/', payload);
}

export async function getAllSections(pageSize = 100) {
  const all = [];
  let skip = 0;
  while (true) {
    const response = await getSections({ skip, limit: pageSize });
    const batch = response.data || [];
    all.push(...batch);
    if (batch.length < pageSize) {
      break;
    }
    skip += pageSize;
  }
  return all;
}

export async function getTeacherSectionsAnalytics() {
  return await apiClient.get('/analytics/teacher/sections');
}
