import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { mergeLookupItems } from '../services/paginatedLookups';
import { loadBatchOptions } from '../services/academicAdminLookups';

export default function SemestersPage() {
  const [batches, setBatches] = useState([]);

  async function loadBatchLookupOptions({ query }) {
    const options = await loadBatchOptions(query, '__any_program__', undefined, { requireProgram: false });
    setBatches((current) =>
      mergeLookupItems(
        current,
        options.map((item) => ({
          id: item.value,
          name: item.name,
          code: item.code,
          public_id: item.public_id,
          display_label: item.display_label,
          label: item.label
        }))
      )
    );
    return options;
  }

  const batchNameById = useMemo(
    () =>
      Object.fromEntries(
        batches.map((batch) => [batch.id, batch.display_label || batch.label || `${batch.name} (${batch.public_id || batch.code || 'Batch'})`])
      ),
    [batches]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      {
        name: 'batch_id',
        label: 'Batch',
        type: 'select',
        searchable: true,
        placeholder: 'All Batches',
        loadOptions: loadBatchLookupOptions,
        selectedLabelResolver: ({ filterValues }) => batchNameById[filterValues.batch_id] || ''
      },
      { name: 'semester_number', label: 'Semester Number', type: 'number', min: 1, max: 12, nullable: true },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [batchNameById]
  );

  const createFields = useMemo(
    () => [
      {
        name: 'batch_id',
        label: 'Batch',
        type: 'select',
        searchable: true,
        required: true,
        placeholder: 'Search batch',
        loadOptions: loadBatchLookupOptions,
        selectedLabelResolver: ({ createValues }) => batchNameById[createValues.batch_id] || ''
      },
      { name: 'semester_number', label: 'Semester Number', type: 'number', min: 1, max: 12, required: true },
      { name: 'label', label: 'Label', required: true }
    ],
    [batchNameById]
  );

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
      { key: 'batch_id', label: 'Batch', render: (row) => batchNameById[row.batch_id] || '-' },
      { key: 'semester_number', label: 'Semester' },
      { key: 'label', label: 'Label' },
      { key: 'academic_year_label', label: 'Academic Year', render: (row) => row.academic_year_label || '-' },
      { key: 'university_code', label: 'University', render: (row) => row.university_code || row.university_name || '-' }
    ],
    [batchNameById]
  );

  return <EntityManager title="Semesters" endpoint="/semesters/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
