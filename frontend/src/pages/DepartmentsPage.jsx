import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function DepartmentsPage() {
  const [faculties, setFaculties] = useState([]);

  useEffect(() => {
    async function loadFaculties() {
      try {
        const response = await apiClient.get('/faculties/', { params: { skip: 0, limit: 100 } });
        setFaculties(response.data || []);
      } catch {
        setFaculties([]);
      }
    }
    loadFaculties();
  }, []);

  const facultyOptions = useMemo(
    () => faculties.map((faculty) => ({ value: faculty.id, label: `${faculty.name} (${faculty.code})` })),
    [faculties]
  );

  const facultyNameById = useMemo(
    () => Object.fromEntries(faculties.map((faculty) => [faculty.id, faculty.name])),
    [faculties]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      { name: 'faculty_id', label: 'Faculty', type: 'select', options: facultyOptions, placeholder: 'All Faculties' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [facultyOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Department Name', required: true },
      { name: 'code', label: 'Department Code', required: true },
      { name: 'faculty_id', label: 'Faculty', type: 'select', options: facultyOptions, nullable: true }
    ],
    [facultyOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Department' },
      { key: 'code', label: 'Code' },
      { key: 'faculty_id', label: 'Faculty', render: (row) => facultyNameById[row.faculty_id] || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [facultyNameById]
  );

  return (
    <EntityManager
      title="Departments"
      endpoint="/departments/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
    />
  );
}
