import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function BranchesPage() {
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
    () => departments.map((department) => ({ value: department.code, label: `${department.name} (${department.code})` })),
    [departments]
  );

  const departmentNameByCode = useMemo(
    () => Object.fromEntries(departments.map((department) => [department.code, department.name])),
    [departments]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      { name: 'department_code', label: 'Department', type: 'select', options: departmentOptions, placeholder: 'All Departments' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [departmentOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'name', label: 'Branch Name', required: true },
      { name: 'code', label: 'Branch Code', required: true },
      { name: 'department_code', label: 'Department', type: 'select', options: departmentOptions, required: true },
      { name: 'university_name', label: 'University Name', defaultValue: 'Medi-Caps University' },
      { name: 'university_code', label: 'University Code', defaultValue: 'MEDICAPS' }
    ],
    [departmentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Branch' },
      { key: 'code', label: 'Code' },
      { key: 'department_code', label: 'Department', render: (row) => departmentNameByCode[row.department_code] || row.department_name || row.department_code || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [departmentNameByCode]
  );

  return (
    <EntityManager
      title="Branches"
      endpoint="/branches/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
    />
  );
}
