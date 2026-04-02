import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { mergeLookupItems, searchLookupOptions } from '../services/paginatedLookups';

export default function FacultiesPage() {
  const [universities, setUniversities] = useState([]);

  async function loadUniversityOptions({ query }) {
    const options = await searchLookupOptions({
      path: '/universities/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({
        value: item.id,
        label: item.display_label || `${item.university_name} (${item.public_id || item.university_id})`,
        university_name: item.university_name,
        university_id: item.university_id
      })
    });
    setUniversities((current) =>
      mergeLookupItems(
        current,
        options.map((item) => ({
          id: item.value,
          university_name: item.university_name,
          university_id: item.university_id
        }))
      )
    );
    return options;
  }

  const universityNameById = useMemo(
    () => Object.fromEntries(universities.map((item) => [item.id, item.university_name])),
    [universities]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search' },
      {
        name: 'university_id',
        label: 'University',
        type: 'select',
        searchable: true,
        placeholder: 'All Universities',
        loadOptions: loadUniversityOptions,
        selectedLabelResolver: ({ filterValues }) => universityNameById[filterValues.university_id] || ''
      },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [universityNameById]
  );

  const createFields = useMemo(
    () => [
      { name: 'faculty_id', label: 'Legacy Business ID (Optional)', nullable: true },
      { name: 'faculty_name', label: 'Faculty Name', required: true },
      { name: 'faculty_code', label: 'Faculty Code', required: true },
      {
        name: 'university_id',
        label: 'University',
        type: 'select',
        searchable: true,
        required: true,
        placeholder: 'Search university',
        loadOptions: loadUniversityOptions,
        selectedLabelResolver: ({ createValues }) => universityNameById[createValues.university_id] || ''
      }
    ],
    [universityNameById]
  );

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || row.faculty_id || '-' },
      { key: 'faculty_name', label: 'Faculty', render: (row) => row.faculty_name || row.name || '-' },
      { key: 'faculty_code', label: 'Code', render: (row) => row.faculty_code || row.code || '-' },
      { key: 'university_name', label: 'University', render: (row) => row.university_name || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    []
  );

  return <EntityManager title="Faculties" endpoint="/faculties/" filters={filters} createFields={createFields} columns={columns} enableEdit enableDelete />;
}
