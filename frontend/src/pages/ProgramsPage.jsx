import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function ProgramsPage() {
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    async function loadDepartments() {
      try {
        const response = await apiClient.get('/departments/', { params: { skip: 0, limit: 200 } });
        setDepartments(response.data || []);
      } catch {
        setDepartments([]);
      }
    }
    loadDepartments();
  }, []);

  const departmentOptions = useMemo(
    () => departments.map((department) => ({ value: department.id, label: `${department.name} (${department.code})` })),
    [departments]
  );

  const departmentNameById = useMemo(
    () => Object.fromEntries(departments.map((department) => [department.id, department.name])),
    [departments]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      { name: 'department_id', label: 'Department', type: 'select', options: departmentOptions, placeholder: 'All Departments' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [departmentOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Program Name', required: true },
      { name: 'code', label: 'Program Code', required: true },
      { name: 'department_id', label: 'Department', type: 'select', options: departmentOptions, required: true },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [departmentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Program' },
      { key: 'code', label: 'Code' },
      { key: 'department_id', label: 'Department', render: (row) => departmentNameById[row.department_id] || row.department_id || '-' },
      { key: 'description', label: 'Description' }
    ],
    [departmentNameById]
  );

  return <EntityManager title="Programs" endpoint="/programs/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
