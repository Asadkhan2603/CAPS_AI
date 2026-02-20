import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search', placeholder: 'Name / code' }
];

const createFields = [
  { name: 'name', label: 'Subject Name', required: true },
  { name: 'code', label: 'Subject Code', required: true },
  { name: 'description', label: 'Description', nullable: true }
];

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'code', label: 'Code' },
  { key: 'description', label: 'Description' }
];

export default function SubjectsPage() {
  return <EntityManager title="Subjects" endpoint="/subjects/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
