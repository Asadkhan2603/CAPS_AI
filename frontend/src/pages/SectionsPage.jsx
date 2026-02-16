import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'q', label: 'Search' },
  { name: 'academic_year', label: 'Academic Year' }
];

const createFields = [
  { name: 'name', label: 'Section Name', required: true },
  { name: 'program', label: 'Program', required: true },
  { name: 'academic_year', label: 'Academic Year', required: true },
  { name: 'semester', label: 'Semester', type: 'number', min: 1, max: 12, defaultValue: 1, required: true }
];

const columns = [
  { key: 'name', label: 'Section' },
  { key: 'program', label: 'Program' },
  { key: 'academic_year', label: 'Academic Year' },
  { key: 'semester', label: 'Semester' }
];

export default function SectionsPage() {
  return <EntityManager title="Sections" endpoint="/sections/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
