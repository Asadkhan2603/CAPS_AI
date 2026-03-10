import { useMemo } from 'react';
import EntityManager from '../components/ui/EntityManager';

export default function SubjectsPage() {
  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Name / code' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    []
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Subject Name', required: true },
      { name: 'code', label: 'Subject Code', required: true },
      { name: 'description', label: 'Description', nullable: true }
    ],
    []
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
      { key: 'name', label: 'Name' },
      { key: 'code', label: 'Code' },
      { key: 'description', label: 'Description' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    []
  );

  return (
    <EntityManager
      title="Subjects"
      endpoint="/subjects/"
      filters={filters}
      createFields={createFields}
      editFields={editFields}
      columns={columns}
      enableEdit
      enableDelete
      createTransform={(payload) => ({
        ...payload,
        code: String(payload.code || '').trim().toUpperCase(),
        description: payload.description || null
      })}
      updateTransform={(payload) => ({
        ...payload,
        code: String(payload.code || '').trim().toUpperCase(),
        description: payload.description || null
      })}
    />
  );
}
