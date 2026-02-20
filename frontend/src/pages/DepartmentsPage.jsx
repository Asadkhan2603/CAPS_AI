import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search' },
  { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
];

const createFields = [
  { name: 'name', label: 'Department Name', required: true },
  { name: 'code', label: 'Department Code', required: true },
  { name: 'university_name', label: 'University Name', defaultValue: 'Medi-Caps University' },
  { name: 'university_code', label: 'University Code', defaultValue: 'MEDICAPS' }
];

const columns = [
  { key: 'name', label: 'Department' },
  { key: 'code', label: 'Code' },
  { key: 'university_name', label: 'University' },
  { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
];

export default function DepartmentsPage() {
  return (
    <EntityManager
      title="Departments"
      endpoint="/departments/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
    />
  );
}
