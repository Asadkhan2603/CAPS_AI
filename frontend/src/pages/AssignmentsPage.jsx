import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search', placeholder: 'Title' },
  { name: 'subject_id', label: 'Subject ID' },
  { name: 'section_id', label: 'Section ID' }
];

const createFields = [
  { name: 'title', label: 'Title', required: true },
  { name: 'description', label: 'Description', nullable: true },
  { name: 'subject_id', label: 'Subject ID', nullable: true },
  { name: 'section_id', label: 'Section ID', nullable: true },
  { name: 'total_marks', label: 'Total Marks', type: 'number', min: 1, max: 1000, defaultValue: 100, required: true }
];

const columns = [
  { key: 'title', label: 'Title' },
  { key: 'subject_id', label: 'Subject ID' },
  { key: 'section_id', label: 'Section ID' },
  { key: 'total_marks', label: 'Marks' }
];

export default function AssignmentsPage() {
  return <EntityManager title="Assignments" endpoint="/assignments/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
