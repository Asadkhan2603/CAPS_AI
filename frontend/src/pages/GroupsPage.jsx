import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { getAllSections } from '../services/sectionsApi';

export default function GroupsPage() {
  const [sections, setSections] = useState([]);

  useEffect(() => {
    async function loadSections() {
      try {
        const rows = await getAllSections(100);
        setSections(rows || []);
      } catch {
        setSections([]);
      }
    }
    loadSections();
  }, []);

  const sectionOptions = useMemo(
    () => sections.map((item) => ({ value: item.id, label: item.name })),
    [sections]
  );
  const sectionNameById = useMemo(
    () => Object.fromEntries(sections.map((item) => [item.id, item.name])),
    [sections]
  );

  const filters = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'q', label: 'Search' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, required: true },
      { name: 'name', label: 'Group Name', required: true },
      { name: 'code', label: 'Group Code', required: true },
      { name: 'description', label: 'Description', nullable: true }
    ],
    [sectionOptions]
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

