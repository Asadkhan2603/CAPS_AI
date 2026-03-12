import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function SpecializationsPage() {
  const [programs, setPrograms] = useState([]);

  useEffect(() => {
    async function loadPrograms() {
      try {
        const response = await apiClient.get('/programs/', { params: { skip: 0, limit: 100 } });
        setPrograms(response.data || []);
      } catch {
        setPrograms([]);
      }
    }
    loadPrograms();
  }, []);

  const programOptions = useMemo(
    () => programs.map((program) => ({ value: program.id, label: `${program.name} (${program.code})` })),
    [programs]
  );

  const programNameById = useMemo(
    () => Object.fromEntries(programs.map((program) => [program.id, program.name])),
    [programs]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      { name: 'program_id', label: 'Program', type: 'select', options: programOptions, placeholder: 'All Programs' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [programOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Specialization Name', required: true },
      { name: 'code', label: 'Specialization Code', required: true },
      { name: 'program_id', label: 'Program', type: 'select', options: programOptions, required: true },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [programOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Specialization' },
      { key: 'code', label: 'Code' },
      { key: 'program_id', label: 'Program', render: (row) => programNameById[row.program_id] || row.program_id || '-' },
      { key: 'description', label: 'Description' }
    ],
    [programNameById]
  );

  return (
    <EntityManager
      title="Specializations"
      endpoint="/specializations/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
    />
  );
}
