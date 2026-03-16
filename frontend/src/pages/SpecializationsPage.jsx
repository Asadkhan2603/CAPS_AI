import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { mergeLookupItems, searchLookupOptions } from '../services/paginatedLookups';

export default function SpecializationsPage() {
  const [programs, setPrograms] = useState([]);

  async function loadProgramOptions({ query }) {
    const options = await searchLookupOptions({
      path: '/programs/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({
        value: item.id,
        label: `${item.program_name || item.name} (${item.program_code || item.code})`,
        program_name: item.program_name || item.name,
        program_code: item.program_code || item.code
      })
    });
    setPrograms((current) =>
      mergeLookupItems(
        current,
        options.map((item) => ({
          id: item.value,
          program_name: item.program_name,
          program_code: item.program_code
        }))
      )
    );
    return options;
  }

  const programNameById = useMemo(
    () => Object.fromEntries(programs.map((program) => [program.id, program.program_name])),
    [programs]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      {
        name: 'program_id',
        label: 'Program',
        type: 'select',
        searchable: true,
        placeholder: 'All Programs',
        loadOptions: loadProgramOptions,
        selectedLabelResolver: ({ filterValues }) => programNameById[filterValues.program_id] || ''
      },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [programNameById]
  );

  const createFields = useMemo(
    () => [
      { name: 'specialization_id', label: 'Specialization ID', nullable: true },
      { name: 'specialization_name', label: 'Specialization Name', required: true },
      { name: 'specialization_code', label: 'Specialization Code', required: true },
      {
        name: 'program_id',
        label: 'Program',
        type: 'select',
        searchable: true,
        required: true,
        placeholder: 'Search program',
        loadOptions: loadProgramOptions,
        selectedLabelResolver: ({ createValues }) => programNameById[createValues.program_id] || ''
      },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [programNameById]
  );

  const columns = useMemo(
    () => [
      { key: 'specialization_id', label: 'Specialization ID', render: (row) => row.specialization_id || '-' },
      { key: 'specialization_name', label: 'Specialization', render: (row) => row.specialization_name || row.name || '-' },
      { key: 'specialization_code', label: 'Code', render: (row) => row.specialization_code || row.code || '-' },
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
