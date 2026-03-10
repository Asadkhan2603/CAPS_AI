import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';

export default function BatchesPage() {
  const { pushToast } = useToast();
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    async function loadLookups() {
      const [programsRes, specializationsRes] = await Promise.allSettled([
        apiClient.get('/programs/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/specializations/', { params: { skip: 0, limit: 100 } })
      ]);
      setPrograms(programsRes.status === 'fulfilled' ? programsRes.value.data || [] : []);
      setSpecializations(specializationsRes.status === 'fulfilled' ? specializationsRes.value.data || [] : []);
    }
    loadLookups();
  }, []);

  const programOptions = useMemo(
    () => programs.map((program) => ({ value: program.id, label: `${program.name} (${program.code})` })),
    [programs]
  );
  const specializationOptions = useMemo(
    () => specializations.map((item) => ({
      value: item.id,
      label: `${item.name} (${item.code})`,
      program_id: item.program_id
    })),
    [specializations]
  );

  const programNameById = useMemo(() => Object.fromEntries(programs.map((item) => [item.id, item.name])), [programs]);
  const specializationNameById = useMemo(
    () => Object.fromEntries(specializations.map((item) => [item.id, item.name])),
    [specializations]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      {
        name: 'program_id',
        label: 'Program',
        type: 'select',
        searchable: true,
        options: programOptions,
        placeholder: 'All Programs'
      },
      {
        name: 'specialization_id',
        label: 'Specialization',
        type: 'select',
        searchable: true,
        options: specializationOptions,
        filterDependsOn: 'program_id',
        filterOptionMatchKey: 'program_id',
        placeholder: 'All Specializations'
      },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [programOptions, specializationOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Batch Name', required: true },
      { name: 'code', label: 'Batch Code', required: true },
      {
        name: 'program_id',
        label: 'Program',
        type: 'select',
        searchable: true,
        options: programOptions,
        required: true,
        placeholder: 'Select Program'
      },
      {
        name: 'specialization_id',
        label: 'Specialization (Optional)',
        type: 'select',
        searchable: true,
        options: specializationOptions,
        dependsOn: 'program_id',
        optionMatchKey: 'program_id',
        requireParentSelection: true,
        nullable: true,
        placeholder: 'Select Specialization (Optional)'
      },
      {
        name: 'start_year',
        label: 'Start Year / Join Year (Optional)',
        type: 'number',
        min: 2000,
        max: 2100,
        nullable: true,
        placeholder: 'Example: 2022'
      },
      {
        name: 'end_year',
        label: 'End Year / Pass-out Year (Optional)',
        type: 'number',
        min: 2000,
        max: 2100,
        nullable: true,
        placeholder: 'Example: 2026 for a 4-year batch starting in 2022'
      }
    ],
    [programOptions, specializationOptions]
  );
  const editFields = useMemo(
    () => [
      ...createFields,
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true }
    ],
    [createFields]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Batch' },
      { key: 'code', label: 'Code' },
      { key: 'program_id', label: 'Program', render: (row) => programNameById[row.program_id] || row.program_id || '-' },
      {
        key: 'specialization_id',
        label: 'Specialization',
        render: (row) => specializationNameById[row.specialization_id] || row.specialization_id || '-'
      },
      { key: 'start_year', label: 'Start' },
      { key: 'end_year', label: 'End' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [programNameById, specializationNameById]
  );

  async function onSeedBatches() {
    setSyncing(true);
    try {
      const response = await apiClient.post('/programs/seed-batches');
      pushToast({
        title: 'Batches synced',
        description: `${response.data?.batch_count ?? 0} batches ensured across ${response.data?.program_count ?? 0} programs.`,
        variant: 'success'
      });
      setReloadToken((prev) => prev + 1);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to seed program batches';
      pushToast({ title: 'Sync failed', description: String(detail), variant: 'error' });
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
        <p>
          Programs now auto-seed base batches from 2022 to the current year. Use manual batch create only for exceptional or specialization-specific cohorts.
        </p>
        <button type="button" className="btn-secondary" onClick={onSeedBatches} disabled={syncing}>
          {syncing ? 'Syncing...' : 'Sync Program Batches'}
        </button>
      </div>
      <EntityManager
        key={reloadToken}
        title="Batches"
        endpoint="/batches/"
        filters={filters}
        createFields={createFields}
        editFields={editFields}
        columns={columns}
        enableEdit
        enableDelete
        createTransform={(payload) => ({
          ...payload,
          code: String(payload.code || '').trim().toUpperCase(),
          specialization_id: payload.specialization_id || null
        })}
        updateTransform={(payload) => ({
          ...payload,
          code: String(payload.code || '').trim().toUpperCase(),
          specialization_id: payload.specialization_id || null
        })}
      />
    </div>
  );
}
