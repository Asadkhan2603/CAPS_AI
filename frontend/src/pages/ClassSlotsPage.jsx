import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

const DAY_OPTIONS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((day) => ({
  value: day,
  label: day
}));

export default function ClassSlotsPage() {
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [offerings, setOfferings] = useState([]);

  useEffect(() => {
    async function loadOfferings() {
      try {
        const response = await apiClient.get('/course-offerings/', { params: { skip: 0, limit: 500 } });
        setOfferings(response.data || []);
      } catch {
        setOfferings([]);
      }
    }
    loadOfferings();
  }, []);

  const offeringOptions = useMemo(
    () =>
      offerings.map((item) => ({
        value: item.id,
        label: `${item.section_id} | ${item.academic_year} | ${item.offering_type}`
      })),
    [offerings]
  );
  const offeringMap = useMemo(
    () => Object.fromEntries(offerings.map((item) => [item.id, `${item.section_id} | ${item.offering_type}`])),
    [offerings]
  );

  const filters = useMemo(
    () => [
      { name: 'course_offering_id', label: 'Offering', type: 'select', options: offeringOptions, placeholder: 'All Offerings' },
      { name: 'day', label: 'Day', type: 'select', options: DAY_OPTIONS, placeholder: 'All Days' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [offeringOptions]
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
      columns={columns}
      enableDelete={!isStudent}
      hideCreate={isStudent}
    />
  );
}

