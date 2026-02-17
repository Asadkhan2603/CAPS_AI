import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

const filters = [
  { name: 'is_active', label: 'Active', type: 'switch' }
];

export default function ClubsPage() {
  const { user } = useAuth();
  const [teachers, setTeachers] = useState([]);

  useEffect(() => {
    async function loadTeachers() {
      try {
        const response = await apiClient.get('/users/');
        setTeachers((response.data || []).filter((item) => item.role === 'teacher'));
      } catch {
        setTeachers([]);
      }
    }
    loadTeachers();
  }, []);

  const teacherOptions = useMemo(
    () => teachers.map((teacher) => ({ value: teacher.id, label: `${teacher.full_name} (${teacher.email})` })),
    [teachers]
  );
  const teacherNameById = useMemo(
    () => Object.fromEntries(teacherOptions.map((item) => [item.value, item.label])),
    [teacherOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Name', required: true },
      { name: 'description', label: 'Description', nullable: true },
      { name: 'coordinator_user_id', label: 'Coordinator', type: 'select', options: teacherOptions, nullable: true, placeholder: 'No Coordinator' }
    ],
    [teacherOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Name' },
      { key: 'description', label: 'Description' },
      { key: 'coordinator_user_id', label: 'Coordinator', render: (row) => teacherNameById[row.coordinator_user_id] || row.coordinator_user_id || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [teacherNameById]
  );

  return (
    <EntityManager
      title="Clubs"
      endpoint="/clubs/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      hideCreate={user?.role !== 'admin'}
      createTransform={(payload) => ({
        ...payload,
        coordinator_user_id: payload.coordinator_user_id || null
      })}
    />
  );
}
