import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { PROGRAM_DURATION_OPTIONS } from '../constants/academicHierarchy';
import { useAuthContext } from '../context/AuthContext';
import { mergeLookupItems, searchLookupOptions } from '../services/paginatedLookups';

export default function ProgramsPage() {
  const { user } = useAuthContext();
  const [departments, setDepartments] = useState([]);

  async function loadDepartmentOptions({ query }) {
    const options = await searchLookupOptions({
      path: '/departments/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({
        value: item.id,
        label: item.display_label || `${item.department_name || item.name} (${item.public_id || item.department_code || item.code})`,
        department_name: item.department_name || item.name,
        department_code: item.department_code || item.code
      })
    });
    setDepartments((current) =>
      mergeLookupItems(
        current,
        options.map((item) => ({
          id: item.value,
          department_name: item.department_name,
          department_code: item.department_code
        }))
      )
    );
    return options;
  }

  const departmentNameById = useMemo(
    () => Object.fromEntries(departments.map((department) => [department.id, department.department_name])),
    [departments]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      {
        name: 'department_id',
        label: 'Department',
        type: 'select',
        searchable: true,
        placeholder: 'All Departments',
        loadOptions: loadDepartmentOptions,
        selectedLabelResolver: ({ filterValues }) => departmentNameById[filterValues.department_id] || ''
      },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [departmentNameById]
  );

  const createFields = useMemo(
    () => [
      { name: 'program_id', label: 'Legacy Business ID (Optional)', nullable: true },
      { name: 'program_name', label: 'Program Name', required: true },
      { name: 'program_code', label: 'Program Code', required: true },
      {
        name: 'department_id',
        label: 'Department',
        type: 'select',
        searchable: true,
        required: true,
        placeholder: 'Search department',
        loadOptions: loadDepartmentOptions,
        selectedLabelResolver: ({ createValues }) => departmentNameById[createValues.department_id] || ''
      },
      {
        name: 'duration_years',
        label: 'Program Duration',
        type: 'select',
        options: PROGRAM_DURATION_OPTIONS,
        required: true,
        defaultValue: 4
      },
      { name: 'degree_type', label: 'Degree Type', nullable: true },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [departmentNameById]
  );

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || row.program_id || '-' },
      { key: 'program_name', label: 'Program', render: (row) => row.program_name || row.name || '-' },
      { key: 'program_code', label: 'Code', render: (row) => row.program_code || row.code || '-' },
      { key: 'department_id', label: 'Department', render: (row) => departmentNameById[row.department_id] || '-' },
      { key: 'degree_type', label: 'Degree Type', render: (row) => row.degree_type || '-' },
      { key: 'duration_years', label: 'Duration (Years)' },
      { key: 'total_semesters', label: 'Total Semesters' },
      { key: 'description', label: 'Description' }
    ],
    [departmentNameById]
  );

  const canManageProgramDuration =
    user?.role === 'admin' && ['super_admin', 'academic_admin', 'department_admin'].includes(user?.admin_type || 'admin');

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
        Total semesters are auto-generated from the selected duration: 1 year = 2 semesters through 5 years = 10 semesters. Base batches are also auto-created from 2022 through the current year.
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
