import { apiClient } from './apiClient';
import { searchLookupOptions } from './paginatedLookups';

export function mergeRows(setter, rows) {
  setter((prev) => {
    const merged = new Map((prev || []).map((item) => [String(item.id), item]));
    (rows || []).forEach((item) => {
      if (item?.id) {
        merged.set(String(item.id), item);
      }
    });
    return Array.from(merged.values());
  });
}

export async function fetchMissingByIds(path, ids, knownIds = new Set()) {
  const missingIds = Array.from(new Set((ids || []).filter(Boolean))).filter((id) => !knownIds.has(id));
  if (!missingIds.length) return [];

  const responses = await Promise.allSettled(
    missingIds.map((id) => apiClient.get(`${path}/${id}`))
  );
  return responses
    .filter((result) => result.status === 'fulfilled')
    .map((result) => result.value.data);
}

export async function loadProgramOptions(query) {
  return searchLookupOptions({
    path: '/programs/',
    q: query,
    params: { is_active: true },
    mapOption: (item) => ({
      value: item.id,
      label: item.display_label || `${item.program_name || item.name} (${item.public_id || item.program_code || item.code})`,
      name: item.program_name || item.name,
      code: item.program_code || item.code,
      public_id: item.public_id,
      display_label: item.display_label,
      department_id: item.department_id
    })
  });
}

export async function loadSpecializationOptions(query, programId) {
  if (!programId) return [];
  return searchLookupOptions({
    path: '/specializations/',
    q: query,
    params: { is_active: true, program_id: programId },
    mapOption: (item) => ({
      value: item.id,
      label: item.display_label || `${item.specialization_name || item.name} (${item.public_id || item.specialization_code || item.code})`,
      name: item.specialization_name || item.name,
      code: item.specialization_code || item.code,
      public_id: item.public_id,
      display_label: item.display_label,
      program_id: item.program_id
    })
  });
}

export async function loadBatchOptions(query, programId, specializationId, options = {}) {
  const requireProgram = options.requireProgram ?? true;
  if (requireProgram && !programId) return [];
  return searchLookupOptions({
    path: '/batches/',
    q: query,
    params: {
      is_active: true,
      program_id: programId && programId !== '__any_program__' ? programId : undefined,
      specialization_id: specializationId || undefined
    },
    mapOption: (item) => ({
      value: item.id,
      label: item.display_label || `${item.name} (${item.public_id || item.code})`,
      name: item.name,
      code: item.code,
      public_id: item.public_id,
      display_label: item.display_label,
      program_id: item.program_id,
      specialization_id: item.specialization_id
    })
  });
}

export async function loadSemesterOptions(query, batchId) {
  if (!batchId) return [];
  return searchLookupOptions({
    path: '/semesters/',
    q: query,
    params: { is_active: true, batch_id: batchId },
    mapOption: (item) => ({
      value: item.id,
      label: item.display_label || item.label,
      public_id: item.public_id,
      display_label: item.display_label,
      batch_id: item.batch_id,
      semester_number: item.semester_number
    })
  });
}

export async function loadSectionOptions(query, batchId, semesterId) {
  if (!batchId || !semesterId) return [];
  return searchLookupOptions({
    path: '/sections/',
    q: query,
    params: { is_active: true, batch_id: batchId, semester_id: semesterId },
    mapOption: (item) => ({
      value: item.id,
      label: item.display_label || `${item.name} (${item.public_id || 'Section'})`,
      name: item.name,
      public_id: item.public_id,
      display_label: item.display_label,
      batch_id: item.batch_id,
      semester_id: item.semester_id,
      program_id: item.program_id,
      specialization_id: item.specialization_id
    })
  });
}

export async function listSectionsForHierarchy(filters = {}) {
  const params = {
    faculty_id: filters.faculty_id || undefined,
    department_id: filters.department_id || undefined,
    program_id: filters.program_id || undefined,
    specialization_id: filters.specialization_id || undefined,
    batch_id: filters.batch_id || undefined,
    semester_id: filters.semester_id || undefined,
    skip: 0,
    limit: 100
  };
  const response = await apiClient.get('/sections/', { params });
  return Array.isArray(response.data) ? response.data : [];
}
