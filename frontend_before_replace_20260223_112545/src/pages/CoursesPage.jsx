import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search', placeholder: 'Name / code' }
];

const createFields = [
  { name: 'name', label: 'Course Name', required: true },
  { name: 'code', label: 'Course Code', required: true },
  { name: 'description', label: 'Description', nullable: true }
];

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'code', label: 'Code' },
  { key: 'description', label: 'Description' }
];

export default function CoursesPage() {
  return (
    <EntityManager
      title="Courses"
      endpoint="/courses/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      hideCreate
      enableDelete={false}
    />
  );
}
