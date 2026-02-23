import { apiClient } from './apiClient';

export async function sendEvaluationChatMessage(payload) {
  const response = await apiClient.post('/ai/evaluate', payload);
  return response.data;
}

export async function getEvaluationChatHistory(studentId, examId, params = {}) {
  const response = await apiClient.get(`/ai/history/${studentId}/${examId}`, { params });
  return response.data;
}
