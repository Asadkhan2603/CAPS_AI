import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { getSections } from '../services/sectionsApi';
import { useAuth } from '../hooks/useAuth';

function canManageEnrollments(user) {
  if (!user) return false;
  if (user.role === 'admin') return true;
  if (user.role !== 'teacher') return false;
  const extensions = user.extended_roles || [];
  return extensions.includes('year_head') || extensions.includes('class_coordinator');
}

export default function EnrollmentsPage() {
  const { user } = useAuth();
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);

  useEffect(() => {
    async function loadLookups() {
      try {
        const sectionsReq = getSections({ skip: 0, limit: 100 });
        const [sectionsRes, studentsRes] = await Promise.all([
          sectionsReq,
          apiClient.get('/students/', { params: { skip: 0, limit: 100 } })
        ]);
        setSections(sectionsRes.data || []);
        setStudents(studentsRes.data || []);
      } catch {
        setSections([]);
        setStudents([]);
      }
    }
    loadLookups();
  }, []);

  const sectionOptions = useMemo(
    () => sections.map((item) => ({ value: item.id, label: item.name })),
    [sections]
  );
  const studentOptions = useMemo(
    () => students.map((item) => ({ value: item.roll_number, label: `${item.full_name} (${item.roll_number})` })),
    [students]
  );
  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );
  const studentNameById = useMemo(() => {
    const map = {};
    for (const item of students) {
      const label = `${item.full_name} (${item.roll_number})`;
      if (item.id) map[item.id] = label;
      if (item.roll_number) map[item.roll_number] = label;
    }
    return map;
  }, [students]);
  const filters = useMemo(
    () => [
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'student_id', label: 'Enrollment Number', type: 'select', options: studentOptions, placeholder: 'All Students' }
    ],
    [sectionOptions, studentOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, required: true },
      { name: 'student_id', label: 'Enrollment Number', type: 'select', options: studentOptions, required: true }
    ],
    [sectionOptions, studentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'class_id', label: 'Section', render: (row) => sectionNameById[row.class_id] || row.class_id },
      {
        key: 'student_id',
        label: 'Student',
        render: (row) =>
          studentNameById[row.student_id] ||
          studentNameById[row.student_roll_number] ||
          row.student_roll_number ||
          row.student_id
      },
      { key: 'assigned_by_user_id', label: 'Assigned By' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [sectionNameById, studentNameById]
  );

  return (
    <EntityManager
      title="Enrollments"
      endpoint="/enrollments/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      hideCreate={!canManageEnrollments(user)}
    />
  );
}
