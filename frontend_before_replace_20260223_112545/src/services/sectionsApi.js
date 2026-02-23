import { apiClient } from './apiClient';

export async function getSections(params = {}) {
  try {
    return await apiClient.get('/sections/', { params });
  } catch (err) {
    if (err?.response?.status !== 404) {
      throw err;
    }
    return await apiClient.get('/classes/', { params });
  }
}

export async function createSection(payload) {
  try {
    return await apiClient.post('/sections/', payload);
  } catch (err) {
    if (err?.response?.status !== 404) {
      throw err;
    }
    return await apiClient.post('/classes/', payload);
  }
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
  try {
    return await apiClient.get('/analytics/teacher/sections');
  } catch (err) {
    if (err?.response?.status !== 404) {
      throw err;
    }
    return await apiClient.get('/analytics/teacher/classes');
  }
}
