import { apiClient } from './apiClient';

export async function getTimetableShifts() {
  const response = await apiClient.get('/timetables/shifts');
  return response.data?.shifts || [];
}

export async function generateTimetableGrid(payload) {
  const response = await apiClient.post('/timetables/generate-grid', payload);
  return response.data;
}

export async function createTimetable(payload) {
  const response = await apiClient.post('/timetables/', payload);
  return response.data;
}

export async function updateTimetable(timetableId, payload) {
  const response = await apiClient.put(`/timetables/${timetableId}`, payload);
  return response.data;
}

export async function publishTimetable(timetableId) {
  const response = await apiClient.post(`/timetables/${timetableId}/publish`);
  return response.data?.timetable || null;
}

export async function listClassTimetables(classId, status) {
  const response = await apiClient.get(`/timetables/class/${classId}`, {
    params: status ? { status } : undefined
  });
  return response.data || [];
}

export async function getMyTimetable(semester) {
  const response = await apiClient.get('/timetables/my', {
    params: semester ? { semester } : undefined
  });
  return response.data;
}

