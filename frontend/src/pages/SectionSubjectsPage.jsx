import EntityManager from '../components/ui/EntityManager';

const filters = [
  { name: 'section_id', label: 'Section ID' },
  { name: 'subject_id', label: 'Subject ID' }
];

const createFields = [
  { name: 'section_id', label: 'Section ID', required: true },
  { name: 'subject_id', label: 'Subject ID', required: true },
  { name: 'teacher_user_id', label: 'Teacher User ID', nullable: true }
];

const columns = [
  { key: 'section_id', label: 'Section ID' },
  { key: 'subject_id', label: 'Subject ID' },
  { key: 'teacher_user_id', label: 'Teacher ID' },
  { key: 'is_active', label: 'Active', render: (row) => String(row.is_active) }
];

export default function SectionSubjectsPage() {
  return (
    <EntityManager
      title="Section Subjects"
      endpoint="/section-subjects/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
    />
  );
}
