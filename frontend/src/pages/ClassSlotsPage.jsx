import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { getAllSections } from '../services/sectionsApi';

const DAY_OPTIONS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((day) => ({
  value: day,
  label: day
}));

export default function ClassSlotsPage() {
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [offerings, setOfferings] = useState([]);
  const [sections, setSections] = useState([]);

  useEffect(() => {
    async function loadOfferings() {
      const [offeringsRes, sectionsRes] = await Promise.allSettled([
        apiClient.get('/course-offerings/', { params: { skip: 0, limit: 500 } }),
        getAllSections(100)
      ]);
      setOfferings(offeringsRes.status === 'fulfilled' ? offeringsRes.value.data || [] : []);
      setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value || [] : []);
    }
    loadOfferings();
  }, []);

  const sectionOptions = useMemo(
    () =>
      sections.map((item) => ({
        value: item.id,
        label: item.name
      })),
    [sections]
  );
  const sectionMap = useMemo(
    () => Object.fromEntries(sections.map((item) => [item.id, item.name])),
    [sections]
  );

  const offeringOptions = useMemo(
    () =>
      offerings.map((item) => ({
        value: item.id,
        label: `${sectionMap[item.section_id] || item.section_name || item.section_id} | ${item.academic_year} | ${item.offering_type}`
      })),
    [offerings, sectionMap]
  );
  const offeringMap = useMemo(
    () =>
      Object.fromEntries(
        offerings.map((item) => [
          item.id,
          `${sectionMap[item.section_id] || item.section_name || item.section_id} | ${item.offering_type}`
        ])
      ),
    [offerings, sectionMap]
  );

  const filters = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'course_offering_id', label: 'Offering', type: 'select', options: offeringOptions, placeholder: 'All Offerings' },
      { name: 'day', label: 'Day', type: 'select', options: DAY_OPTIONS, placeholder: 'All Days' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [offeringOptions, sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'course_offering_id', label: 'Offering', type: 'select', options: offeringOptions, required: true },
      { name: 'day', label: 'Day', type: 'select', options: DAY_OPTIONS, required: true },
      { name: 'start_time', label: 'Start Time', placeholder: 'HH:MM', required: true },
      { name: 'end_time', label: 'End Time', placeholder: 'HH:MM', required: true },
      { name: 'room_code', label: 'Room / Lab', required: true }
    ],
    [offeringOptions]
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
      { key: 'course_offering_id', label: 'Offering', render: (row) => offeringMap[row.course_offering_id] || row.course_offering_id || '-' },
      { key: 'day', label: 'Day' },
      { key: 'start_time', label: 'Start' },
      { key: 'end_time', label: 'End' },
      { key: 'room_code', label: 'Room' }
    ],
    [offeringMap]
  );

  return (
    <EntityManager
      title="Class Slots"
      endpoint={isStudent ? '/class-slots/my' : '/class-slots/'}
      filters={isStudent ? [] : filters}
      createFields={createFields}
      editFields={editFields}
      columns={columns}
      enableEdit={!isStudent}
      enableDelete={!isStudent}
      hideCreate={isStudent}
    />
  );
}
