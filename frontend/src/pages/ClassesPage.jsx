import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'course_id', label: 'Course ID' },
  { name: 'year_id', label: 'Year ID' }
];

const createFields = [
  { name: 'course_id', label: 'Course ID', required: true },
  { name: 'year_id', label: 'Year ID', required: true },
  { name: 'name', label: 'Class Name', required: true },
  { name: 'section', label: 'Section', nullable: true },
  { name: 'class_coordinator_user_id', label: 'Coordinator User ID', nullable: true }
];

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'course_id', label: 'Course ID' },
  { key: 'year_id', label: 'Year ID' },
  { key: 'section', label: 'Section' },
  { key: 'class_coordinator_user_id', label: 'Coordinator' }
];

export default function ClassesPage() {
  return <EntityManager title="Classes" endpoint="/classes/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
