import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'course_id', label: 'Course ID', placeholder: 'Filter by course id' }
];

const createFields = [
  { name: 'course_id', label: 'Course ID', required: true },
  { name: 'year_number', label: 'Year Number', type: 'number', min: 1, max: 10, required: true, defaultValue: 1 },
  { name: 'label', label: 'Label', required: true }
];

const columns = [
  { key: 'course_id', label: 'Course ID' },
  { key: 'year_number', label: 'Year' },
  { key: 'label', label: 'Label' }
];

export default function YearsPage() {
  return <EntityManager title="Years" endpoint="/years/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
