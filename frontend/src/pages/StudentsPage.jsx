import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function StudentsPage() {
  const [sections, setSections] = useState([]);

  useEffect(() => {
    async function loadSections() {
      try {
        const response = await apiClient.get('/sections/', { params: { skip: 0, limit: 100 } });
        setSections(response.data || []);
      } catch {
        setSections([]);
      }
    }
    loadSections();
  }, []);

  const sectionOptions = useMemo(
    () =>
      sections.map((section) => ({
        value: section.id,
        label: `${section.name} (${section.program} - ${section.academic_year})`
      })),
    [sections]
  );

  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Name / roll / email' },
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' }
    ],
    [sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'full_name', label: 'Full Name', required: true },
      { name: 'roll_number', label: 'Roll Number', required: true },
      { name: 'email', label: 'Email', nullable: true },
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, nullable: true, placeholder: 'No Section' }
    ],
    [sectionOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'roll_number', label: 'Roll Number' },
      { key: 'email', label: 'Email' },
      { key: 'section_id', label: 'Section', render: (row) => sectionNameById[row.section_id] || row.section_id || '-' }
    ],
    [sectionNameById]
  );

  return <EntityManager title="Students" endpoint="/students/" filters={filters} createFields={createFields} columns={columns} enableDelete />;
}
