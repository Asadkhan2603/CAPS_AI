import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search' },
  { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
];

const createFields = [
  { name: 'university_id', label: 'University ID', required: true },
  { name: 'university_name', label: 'University Name', required: true }
];

const columns = [
  { key: 'university_id', label: 'University ID' },
  { key: 'university_name', label: 'University Name' },
  { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
];

export default function UniversitiesPage() {
  return (
    <EntityManager
      title="Universities"
      endpoint="/universities/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableEdit
      enableDelete
    />
  );
}
