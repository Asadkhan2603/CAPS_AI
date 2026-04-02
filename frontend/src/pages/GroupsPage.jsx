import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { mergeLookupItems, searchLookupOptions } from '../services/paginatedLookups';

export default function GroupsPage() {
  const [sections, setSections] = useState([]);

  async function loadSectionOptions({ query }) {
    const options = await searchLookupOptions({
      path: '/sections/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({
        value: item.id,
        label: item.name,
        id: item.id,
        name: item.name
      })
    });
    setSections((current) =>
      mergeLookupItems(
        current,
        options.map((item) => ({
          id: item.id,
          name: item.name
        }))
      )
    );
    return options;
  }

  const sectionNameById = useMemo(
    () => Object.fromEntries(sections.map((item) => [item.id, item.name])),
    [sections]
  );

  const filters = useMemo(
    () => [
      {
        name: 'section_id',
        label: 'Section',
        type: 'select',
        searchable: true,
        placeholder: 'All Sections',
        loadOptions: loadSectionOptions,
        selectedLabelResolver: ({ filterValues }) => sectionNameById[filterValues.section_id] || ''
      },
      { name: 'q', label: 'Search' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [sectionNameById]
  );

  const createFields = useMemo(
    () => [
      {
        name: 'section_id',
        label: 'Section',
        type: 'select',
        searchable: true,
        required: true,
        placeholder: 'Search section',
        loadOptions: loadSectionOptions,
        selectedLabelResolver: ({ createValues }) => sectionNameById[createValues.section_id] || ''
      },
      { name: 'name', label: 'Group Name', required: true },
      { name: 'code', label: 'Group Code', required: true },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [sectionNameById]
  );

  const columns = useMemo(
    () => [
      { key: 'section_id', label: 'Section', render: (row) => sectionNameById[row.section_id] || row.section_id || '-' },
      { key: 'name', label: 'Group' },
      { key: 'code', label: 'Code' },
      { key: 'description', label: 'Description' }
    ],
    [sectionNameById]
  );

  return <EntityManager title="Groups" endpoint="/groups/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}

