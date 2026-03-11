import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function SemestersPage() {
  const [batches, setBatches] = useState([]);

  useEffect(() => {
    async function loadBatches() {
      try {
        const response = await apiClient.get('/batches/', { params: { skip: 0, limit: 300 } });
        setBatches(response.data || []);
      } catch {
        setBatches([]);
      }
    }
    loadBatches();
  }, []);

  const batchOptions = useMemo(
    () => batches.map((batch) => ({ value: batch.id, label: `${batch.name} (${batch.code})` })),
    [batches]
  );
  const batchNameById = useMemo(() => Object.fromEntries(batches.map((batch) => [batch.id, batch.name])), [batches]);

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      { name: 'batch_id', label: 'Batch', type: 'select', options: batchOptions, placeholder: 'All Batches' },
      { name: 'semester_number', label: 'Semester Number', type: 'number', min: 1, max: 12, nullable: true },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [batchOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'batch_id', label: 'Batch', type: 'select', options: batchOptions, required: true },
      { name: 'semester_number', label: 'Semester Number', type: 'number', min: 1, max: 12, required: true },
      { name: 'label', label: 'Label', required: true }
    ],
    [batchOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'batch_id', label: 'Batch', render: (row) => batchNameById[row.batch_id] || row.batch_id || '-' },
      { key: 'semester_number', label: 'Semester' },
      { key: 'label', label: 'Label' },
      { key: 'academic_year_label', label: 'Academic Year', render: (row) => row.academic_year_label || '-' },
      { key: 'university_code', label: 'University', render: (row) => row.university_code || row.university_name || '-' }
    ],
    [batchNameById]
  );

  return <EntityManager title="Semesters" endpoint="/semesters/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
