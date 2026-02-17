import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
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
  const [classes, setClasses] = useState([]);
  const [students, setStudents] = useState([]);

  useEffect(() => {
    async function loadLookups() {
      try {
        const [classesRes, studentsRes] = await Promise.all([
          apiClient.get('/classes/', { params: { skip: 0, limit: 100 } }),
          apiClient.get('/students/', { params: { skip: 0, limit: 100 } })
        ]);
        setClasses(classesRes.data || []);
        setStudents(studentsRes.data || []);
      } catch {
        setClasses([]);
        setStudents([]);
      }
    }
    loadLookups();
  }, []);

  const classOptions = useMemo(
    () => classes.map((item) => ({ value: item.id, label: item.name })),
    [classes]
  );
  const studentOptions = useMemo(
    () => students.map((item) => ({ value: item.id, label: `${item.full_name} (${item.roll_number})` })),
    [students]
  );
  const classNameById = useMemo(
    () => Object.fromEntries(classOptions.map((item) => [item.value, item.label])),
    [classOptions]
  );
  const studentNameById = useMemo(
    () => Object.fromEntries(studentOptions.map((item) => [item.value, item.label])),
    [studentOptions]
  );
  const filters = useMemo(
    () => [
      { name: 'class_id', label: 'Class', type: 'select', options: classOptions, placeholder: 'All Classes' },
      { name: 'student_id', label: 'Student', type: 'select', options: studentOptions, placeholder: 'All Students' }
    ],
    [classOptions, studentOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'class_id', label: 'Class', type: 'select', options: classOptions, required: true },
      { name: 'student_id', label: 'Student', type: 'select', options: studentOptions, required: true }
    ],
    [classOptions, studentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'class_id', label: 'Class', render: (row) => classNameById[row.class_id] || row.class_id },
      { key: 'student_id', label: 'Student', render: (row) => studentNameById[row.student_id] || row.student_id },
      { key: 'assigned_by_user_id', label: 'Assigned By' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [classNameById, studentNameById]
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
