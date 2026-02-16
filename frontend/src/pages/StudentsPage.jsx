import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search', placeholder: 'Name / roll / email' },
  { name: 'section_id', label: 'Section ID' }
];

const createFields = [
  { name: 'full_name', label: 'Full Name', required: true },
  { name: 'roll_number', label: 'Roll Number', required: true },
  { name: 'email', label: 'Email', nullable: true },
  { name: 'section_id', label: 'Section ID', nullable: true }
];

const columns = [
  { key: 'full_name', label: 'Name' },
  { key: 'roll_number', label: 'Roll Number' },
  { key: 'email', label: 'Email' },
  { key: 'section_id', label: 'Section' }
];

export default function StudentsPage() {
  return <EntityManager title="Students" endpoint="/students/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
