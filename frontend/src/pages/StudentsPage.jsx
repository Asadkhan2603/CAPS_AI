import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function StudentsPage() {
  const [classes, setClasses] = useState([]);

  useEffect(() => {
    async function loadClasses() {
      try {
        const response = await apiClient.get('/classes/', { params: { skip: 0, limit: 200 } });
        setClasses(response.data || []);
      } catch {
        setClasses([]);
      }
    }
    loadClasses();
  }, []);

  const classOptions = useMemo(
    () =>
      classes.map((item) => ({
        value: item.id,
        label: item.name
      })),
    [classes]
  );

  const classNameById = useMemo(
    () => Object.fromEntries(classOptions.map((item) => [item.value, item.label])),
    [classOptions]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Name / roll / email' },
      { name: 'class_id', label: 'Class', type: 'select', options: classOptions, placeholder: 'All Classes' }
    ],
    [classOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'full_name', label: 'Full Name', required: true },
      { name: 'roll_number', label: 'Roll Number', required: true },
      { name: 'email', label: 'Email', nullable: true },
      { name: 'class_id', label: 'Class', type: 'select', options: classOptions, nullable: true, placeholder: 'No Class' }
    ],
    [classOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'roll_number', label: 'Roll Number' },
      { key: 'email', label: 'Email' },
      { key: 'class_id', label: 'Class', render: (row) => classNameById[row.class_id] || row.class_id || '-' }
    ],
    [classNameById]
  );

  return <EntityManager title="Students" endpoint="/students/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
