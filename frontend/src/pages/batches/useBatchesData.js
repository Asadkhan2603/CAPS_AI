import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { searchLookupOptions } from '../../services/paginatedLookups';
import { formatApiError } from '../../utils/apiError';

function mergeById(setter, rows) {
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

export function useBatchesData({
  limit,
  programFilter,
  pushToast,
  searchQuery,
  showInactive,
  skip
}) {
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');

  async function hydrateBatchRelations(batchRows) {
    const programIds = Array.from(new Set((batchRows || []).map((item) => item.program_id).filter(Boolean)));
    const specializationIds = Array.from(new Set((batchRows || []).map((item) => item.specialization_id).filter(Boolean)));

    const knownProgramIds = new Set(programs.map((item) => item.id));
    const knownSpecializationIds = new Set(specializations.map((item) => item.id));

    const missingProgramIds = programIds.filter((id) => !knownProgramIds.has(id));
    const missingSpecializationIds = specializationIds.filter((id) => !knownSpecializationIds.has(id));

    const [programResponses, specializationResponses] = await Promise.all([
      Promise.allSettled(missingProgramIds.map((id) => apiClient.get(`/programs/${id}`))),
      Promise.allSettled(missingSpecializationIds.map((id) => apiClient.get(`/specializations/${id}`)))
    ]);

    mergeById(
      setPrograms,
      programResponses
        .filter((result) => result.status === 'fulfilled')
        .map((result) => result.value.data)
    );
    mergeById(
      setSpecializations,
      specializationResponses
        .filter((result) => result.status === 'fulfilled')
        .map((result) => result.value.data)
    );
  }

  async function loadPageData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/batches/', {
        params: {
          skip,
          limit,
          q: searchQuery || undefined,
          program_id: programFilter || undefined,
          is_active: showInactive ? undefined : true
        }
      });
      const batchRows = Array.isArray(response.data) ? response.data : [];
      setBatches(batchRows);
      await hydrateBatchRelations(batchRows);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load batches');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPageData();
  }, [limit, programFilter, searchQuery, showInactive, skip]);

  async function loadProgramOptions(query) {
    const options = await searchLookupOptions({
      path: '/programs/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({ value: item.id, label: `${item.name} (${item.code})`, name: item.name, code: item.code })
    });
    mergeById(setPrograms, options.map((item) => ({ id: item.value, name: item.name, code: item.code })));
    return options;
  }

  async function loadSpecializationOptions(query, currentProgramId) {
    if (!currentProgramId) return [];
    const options = await searchLookupOptions({
      path: '/specializations/',
      q: query,
      params: { is_active: true, program_id: currentProgramId },
      mapOption: (item) => ({
        value: item.id,
        label: `${item.name} (${item.code})`,
        name: item.name,
        code: item.code,
        program_id: item.program_id
      })
    });
    mergeById(
      setSpecializations,
      options.map((item) => ({ id: item.value, name: item.name, code: item.code, program_id: item.program_id }))
    );
    return options;
  }

  async function deleteBatch(batch) {
    if (!globalThis.window?.confirm(`Archive ${batch.name} (${batch.code})?`)) return;

    try {
      await apiClient.delete(`/batches/${batch.id}`);
      pushToast({
        title: 'Batch archived',
        description: `${batch.name} has been archived.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      const message = formatApiError(err, 'Failed to archive batch');
      pushToast({ title: 'Archive failed', description: message, variant: 'error' });
    }
  }

  async function onSeedBatches() {
    setSyncing(true);
    try {
      const response = await apiClient.post('/programs/seed-batches');
      pushToast({
        title: 'Batches synced',
        description: `${response.data?.batch_count ?? 0} batches ensured across ${response.data?.program_count ?? 0} programs.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      const detail = formatApiError(err, 'Failed to sync program batches');
      pushToast({ title: 'Sync failed', description: detail, variant: 'error' });
    } finally {
      setSyncing(false);
    }
  }

  return {
    batches,
    deleteBatch,
    error,
    loadPageData,
    loadProgramOptions,
    loadSpecializationOptions,
    loading,
    onSeedBatches,
    programs,
    setPrograms,
    setSpecializations,
    specializations,
    syncing
  };
}
