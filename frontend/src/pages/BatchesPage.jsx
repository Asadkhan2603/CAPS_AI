import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function BatchesPage() {
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);

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
        label: 'Start Year (Optional)',
        type: 'number',
        min: 2000,
        max: 2100,
        nullable: true,
        placeholder: 'Auto if end year is provided'
      },
      {
        name: 'end_year',
        label: 'End Year (Optional)',
        type: 'number',
        min: 2000,
        max: 2100,
        nullable: true,
        placeholder: 'Auto from program duration if blank'
      }
    ],
    [programOptions, specializationOptions]
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
      { key: 'end_year', label: 'End' }
    ],
    [programNameById, specializationNameById]
  );

  return <EntityManager title="Batches" endpoint="/batches/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
