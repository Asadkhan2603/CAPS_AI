import { apiClient } from './apiClient';

export async function fetchGovernancePolicy() {
  const response = await apiClient.get('/admin/governance/policy');
  return response.data?.policy || {};
}

export async function updateGovernancePolicy(payload) {
  const response = await apiClient.patch('/admin/governance/policy', payload);
  return response.data?.policy || {};
}

export async function fetchGovernanceDashboard() {
  const response = await apiClient.get('/admin/governance/dashboard');
  return response.data || {};
}

export async function fetchGovernanceReviews({ status = '', limit = 100 } = {}) {
  const params = { limit };
  if (status) {
    params.status = status;
  }
  const response = await apiClient.get('/admin/governance/reviews', { params });
  return Array.isArray(response.data) ? response.data : [];
}

export async function createGovernanceReview(payload) {
  const response = await apiClient.post('/admin/governance/reviews', payload);
  return response.data;
}

export async function decideGovernanceReview(reviewId, payload) {
  const response = await apiClient.patch(`/admin/governance/reviews/${reviewId}`, payload);
  return response.data;
}

export async function fetchGovernanceSessions({ status = '', userId = '', limit = 50 } = {}) {
  const params = { limit };
  if (status) {
    params.status = status;
  }
  if (userId) {
    params.user_id = userId;
  }
  const response = await apiClient.get('/admin/governance/sessions', { params });
  return response.data || { items: [], total: 0 };
}
