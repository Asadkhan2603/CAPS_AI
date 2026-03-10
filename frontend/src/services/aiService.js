import { apiClient } from './apiClient';

export async function sendEvaluationChatMessage(payload) {
  const response = await apiClient.post('/ai/evaluate', payload);
  return response.data;
}

export async function getEvaluationChatHistory(studentId, examId, params = {}) {
  const response = await apiClient.get(`/ai/history/${studentId}/${examId}`, { params });
  return response.data;
}

export async function getEvaluationTrace(evaluationId, params = {}) {
  const response = await apiClient.get(`/evaluations/${evaluationId}/trace`, { params });
  return response.data;
}

export async function refreshEvaluationAi(evaluationId) {
  const response = await apiClient.post(`/evaluations/${evaluationId}/ai-refresh`);
  return response.data;
}

export async function getAiOperationsOverview(params = {}) {
  const response = await apiClient.get('/ai/ops/overview', { params });
  return response.data;
}

export async function getAiRuntimeConfig() {
  const response = await apiClient.get('/ai/admin/runtime-config');
  return response.data;
}

export async function updateAiRuntimeConfig(payload) {
  const response = await apiClient.put('/ai/admin/runtime-config', payload);
  return response.data;
}

export async function listAiJobs(params = {}) {
  const response = await apiClient.get('/ai/jobs', { params });
  return response.data;
}

export async function getAiJob(jobId) {
  const response = await apiClient.get(`/ai/jobs/${jobId}`);
  return response.data;
}
