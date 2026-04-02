import { apiClient } from './apiClient';

function buildMultipart({ workflow, sectionId, groupId, file, allowAdminOverride }) {
  const multipart = new FormData();
  multipart.append('workflow', workflow);
  if (sectionId) {
    multipart.append('section_id', sectionId);
  }
  if (groupId) {
    multipart.append('group_id', groupId);
  }
  if (allowAdminOverride) {
    multipart.append('allow_admin_override', 'true');
  }
  multipart.append('file', file);
  return multipart;
}

export async function previewStudentBulkImport(payload) {
  return await apiClient.post('/students/bulk-import/preview', buildMultipart(payload), {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

export async function commitStudentBulkImport(payload) {
  return await apiClient.post('/students/bulk-import/commit', buildMultipart(payload), {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}
