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

export async function listSharedSimilarityViews() {
  const response = await apiClient.get('/ai/ops/similarity/views');
  return response.data;
}

export async function createSharedSimilarityView(payload) {
  const response = await apiClient.post('/ai/ops/similarity/views', payload);
  return response.data;
}

export async function deleteSharedSimilarityView(viewId) {
  const response = await apiClient.delete(`/ai/ops/similarity/views/${viewId}`);
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

export async function getAiSemanticRolloutConfig() {
  const response = await apiClient.get('/ai/admin/semantic-rollout-config');
  return response.data;
}

export async function updateAiSemanticRolloutConfig(payload) {
  const response = await apiClient.put('/ai/admin/semantic-rollout-config', payload);
  return response.data;
}

export async function applyAiSemanticRolloutRecommendations(payload) {
  const response = await apiClient.post('/ai/admin/semantic-rollout-config/apply-recommendations', payload);
  return response.data;
}

export async function approveAiSemanticRolloutRecommendations(payload) {
  const response = await apiClient.post('/ai/admin/semantic-rollout-config/approve-recommendations', payload);
  return response.data;
}

export async function activateAiSemanticRolloutSnapshot(payload) {
  const response = await apiClient.post('/ai/admin/semantic-rollout-config/activate', payload);
  return response.data;
}

export async function rollbackAiSemanticRolloutSnapshot(payload) {
  const response = await apiClient.post('/ai/admin/semantic-rollout-config/rollback', payload);
  return response.data;
}

export async function getAiSemanticRolloutHistory(params = {}) {
  const response = await apiClient.get('/ai/admin/semantic-rollout-config/history', { params });
  return response.data;
}

export async function getAiOpsSemanticThresholdRecommendations() {
  const response = await apiClient.get('/ai/ops/semantic-threshold-recommendations');
  return response.data;
}

export async function applyAiOpsSemanticThresholds(payload) {
  const response = await apiClient.post('/ai/ops/semantic-thresholds/apply', payload);
  return response.data;
}

export async function activateAiOpsSemanticThresholds(payload) {
  const response = await apiClient.post('/ai/ops/semantic-thresholds/activate', payload);
  return response.data;
}

export async function rollbackAiOpsSemanticThresholds(payload) {
  const response = await apiClient.post('/ai/ops/semantic-thresholds/rollback', payload);
  return response.data;
}

export async function getAiOpsSemanticThresholdHistory(params = {}) {
  const response = await apiClient.get('/ai/ops/semantic-threshold-history', { params });
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

export async function getSimilarityCheck(logId) {
  const response = await apiClient.get(`/similarity/checks/${logId}`);
  return response.data;
}

export async function updateSimilarityCheck(logId, payload) {
  const response = await apiClient.patch(`/similarity/checks/${logId}`, payload);
  return response.data;
}

export async function listSimilarityChecks(params = {}) {
  const response = await apiClient.get('/similarity/checks', { params });
  return response.data;
}
