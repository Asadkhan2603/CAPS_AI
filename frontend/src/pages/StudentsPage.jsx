import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { getSections } from '../services/sectionsApi';

export default function StudentsPage() {
  const [sections, setSections] = useState([]);
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    async function loadSections() {
      try {
        const [sectionsRes, groupsRes] = await Promise.allSettled([
          getSections({ skip: 0, limit: 200 }),
          apiClient.get('/groups/', { params: { skip: 0, limit: 300, is_active: true } })
        ]);
        setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value.data || [] : []);
        setGroups(groupsRes.status === 'fulfilled' ? groupsRes.value.data || [] : []);
      } catch {
        setSections([]);
        setGroups([]);
      }
    }
    loadSections();
  }, []);

  const sectionOptions = useMemo(
    () =>
      sections.map((item) => ({
        value: item.id,
        label: item.name
      })),
    [sections]
  );

  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );
  const groupOptions = useMemo(
    () =>
      groups.map((item) => ({
        value: item.id,
        label: item.name,
        section_id: item.section_id
      })),
    [groups]
  );
  const groupNameById = useMemo(
    () => Object.fromEntries(groups.map((item) => [item.id, item.name])),
    [groups]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Name / roll / email' },
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'full_name', label: 'Full Name', required: true },
      { name: 'roll_number', label: 'Roll Number', required: true },
      { name: 'email', label: 'Email', nullable: true },
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, nullable: true, placeholder: 'No Section' },
      {
        name: 'group_id',
        label: 'Group',
        type: 'select',
        options: groupOptions,
        nullable: true,
        placeholder: 'No Group',
        dependsOn: 'class_id',
        optionMatchKey: 'section_id',
        requireParentSelection: true
      }
    ],
    [groupOptions, sectionOptions]
  );

  const editFields = useMemo(
    () => [
      ...createFields,
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true }
    ],
    [createFields]
  );

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'roll_number', label: 'Roll Number' },
      { key: 'email', label: 'Email' },
      { key: 'class_id', label: 'Section', render: (row) => sectionNameById[row.class_id] || row.class_id || '-' },
      { key: 'group_id', label: 'Group', render: (row) => groupNameById[row.group_id] || row.group_id || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [groupNameById, sectionNameById]
  );

  return (
    <EntityManager
      title="Students"
      endpoint="/students/"
      filters={filters}
      createFields={createFields}
      editFields={editFields}
      columns={columns}
      enableEdit
      enableDelete
      createTransform={(payload) => ({
        ...payload,
        email: payload.email || null,
        class_id: payload.class_id || null,
        group_id: payload.group_id || null
      })}
      updateTransform={(payload) => ({
        ...payload,
        email: payload.email || null,
        class_id: payload.class_id || null,
        group_id: payload.group_id || null
      })}
    />
  );
}
