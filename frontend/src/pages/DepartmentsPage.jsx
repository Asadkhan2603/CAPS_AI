import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { mergeLookupItems, searchLookupOptions } from '../services/paginatedLookups';

export default function DepartmentsPage() {
  const [faculties, setFaculties] = useState([]);

  async function loadFacultyOptions({ query }) {
    const options = await searchLookupOptions({
      path: '/faculties/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({
        value: item.id,
        label: item.display_label || `${item.faculty_name || item.name} (${item.public_id || item.faculty_code || item.code})`,
        faculty_name: item.faculty_name || item.name,
        faculty_code: item.faculty_code || item.code
      })
    });
    setFaculties((current) =>
      mergeLookupItems(
        current,
        options.map((item) => ({
          id: item.value,
          faculty_name: item.faculty_name,
          faculty_code: item.faculty_code
        }))
      )
    );
    return options;
  }

  const facultyNameById = useMemo(
    () => Object.fromEntries(faculties.map((faculty) => [faculty.id, faculty.faculty_name])),
    [faculties]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      {
        name: 'faculty_id',
        label: 'Faculty',
        type: 'select',
        searchable: true,
        placeholder: 'All Faculties',
        loadOptions: loadFacultyOptions,
        selectedLabelResolver: ({ filterValues }) => facultyNameById[filterValues.faculty_id] || ''
      },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [facultyNameById]
  );

  const createFields = useMemo(
    () => [
      { name: 'department_id', label: 'Legacy Business ID (Optional)', nullable: true },
      { name: 'department_name', label: 'Department Name', required: true },
      { name: 'department_code', label: 'Department Code', required: true },
      {
        name: 'faculty_id',
        label: 'Faculty',
        type: 'select',
        searchable: true,
        required: true,
        placeholder: 'Search faculty',
        loadOptions: loadFacultyOptions,
        selectedLabelResolver: ({ createValues }) => facultyNameById[createValues.faculty_id] || ''
      }
    ],
    [facultyNameById]
  );

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || row.department_id || '-' },
      { key: 'department_name', label: 'Department', render: (row) => row.department_name || row.name || '-' },
      { key: 'department_code', label: 'Code', render: (row) => row.department_code || row.code || '-' },
      { key: 'faculty_id', label: 'Faculty', render: (row) => facultyNameById[row.faculty_id] || '-' },
      { key: 'university_name', label: 'University', render: (row) => row.university_name || '-' },
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
      enableEdit
      enableDelete
      deleteReviewEnabled
    />
  );
}
