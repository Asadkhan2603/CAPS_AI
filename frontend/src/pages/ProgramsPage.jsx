import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuthContext } from '../context/AuthContext';

export default function ProgramsPage() {
  const { user } = useAuthContext();
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    async function loadDepartments() {
      try {
        const response = await apiClient.get('/departments/', { params: { skip: 0, limit: 100 } });
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

  const departmentCodeById = useMemo(
    () => Object.fromEntries(departments.map((department) => [department.id, department.code])),
    [departments]
  );

  const inferDepartmentCodeFromProgramCode = (programCode) => {
    const text = String(programCode || '').trim();
    if (!text) return '';
    const parts = text.split('-');
    if (parts.length >= 3) {
      return `${parts[0]}-${parts[1]}`;
    }
    return '';
  };

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
      { name: 'duration_years', label: 'Course Duration (Years)', type: 'number', min: 3, max: 5, required: true, defaultValue: 4 },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [departmentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Program' },
      { key: 'code', label: 'Code' },
      {
        key: 'department_id',
        label: 'Department',
        render: (row) =>
          departmentCodeById[row.department_id] || inferDepartmentCodeFromProgramCode(row.code) || '-'
      },
      { key: 'duration_years', label: 'Duration (Years)' },
      { key: 'total_semesters', label: 'Total Semesters' },
      { key: 'description', label: 'Description' }
    ],
    [departmentCodeById]
  );

  const canManageProgramDuration =
    user?.role === 'admin' && ['super_admin', 'academic_admin', 'department_admin'].includes(user?.admin_type || 'admin');

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
        Total Semesters is auto-generated from Course Duration.
      </div>
      <EntityManager
        title="Programs"
        endpoint="/programs/"
        filters={filters}
        createFields={createFields}
        columns={columns}
        enableEdit={canManageProgramDuration}
        enableDelete={canManageProgramDuration}
        hideCreate={!canManageProgramDuration}
      />
    </div>
  );
}
