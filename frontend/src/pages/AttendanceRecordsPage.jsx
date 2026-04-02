import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

const STATUS_OPTIONS = [
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
  { value: 'excused', label: 'Excused' }
];

export default function AttendanceRecordsPage() {
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [slots, setSlots] = useState([]);
  const [students, setStudents] = useState([]);

  useEffect(() => {
    async function loadLookups() {
      if (isStudent) {
        setSlots([]);
        setStudents([]);
        return;
      }
      const [slotsRes, studentsRes] = await Promise.allSettled([
        apiClient.get('/class-slots/', { params: { skip: 0, limit: 500 } }),
        apiClient.get('/students/', { params: { skip: 0, limit: 500 } })
      ]);
      setSlots(slotsRes.status === 'fulfilled' ? slotsRes.value.data || [] : []);
      setStudents(studentsRes.status === 'fulfilled' ? studentsRes.value.data || [] : []);
    }
    loadLookups();
  }, [isStudent]);

  function slotLabel(item) {
    if (!item) return '';
    return item.display_label || `${item.day} ${item.start_time}-${item.end_time} | ${item.public_id || item.room_code}`;
  }

  function studentLabel(item) {
    if (!item) return '';
    return item.display_label || `${item.full_name} (${item.public_id || item.roll_number})`;
  }

  const slotOptions = useMemo(
    () =>
      slots.map((item) => ({
        value: item.id,
        label: slotLabel(item)
      })),
    [slots]
  );
  const studentOptions = useMemo(
    () => students.map((item) => ({ value: item.id, label: studentLabel(item) })),
    [students]
  );
  const slotMap = useMemo(
    () => Object.fromEntries(slots.map((item) => [item.id, slotLabel(item)])),
    [slots]
  );
  const studentMap = useMemo(
    () => Object.fromEntries(students.map((item) => [item.id, studentLabel(item)])),
    [students]
  );

  const filters = useMemo(
    () => [
      { name: 'class_slot_id', label: 'Class Slot', type: 'select', options: slotOptions, placeholder: 'All Slots' },
      { name: 'student_id', label: 'Student', type: 'select', options: studentOptions, placeholder: 'All Students' }
    ],
    [slotOptions, studentOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'class_slot_id', label: 'Class Slot', type: 'select', options: slotOptions, required: true },
      { name: 'student_id', label: 'Student', type: 'select', options: studentOptions, required: true },
      { name: 'status', label: 'Status', type: 'select', options: STATUS_OPTIONS, required: true, defaultValue: 'present' },
      { name: 'note', label: 'Note', nullable: true }
    ],
    [slotOptions, studentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
      { key: 'class_slot_id', label: 'Class Slot', render: (row) => slotMap[row.class_slot_id] || '-' },
      { key: 'student_id', label: 'Student', render: (row) => studentMap[row.student_id] || '-' },
      { key: 'status', label: 'Status' },
      { key: 'marked_at', label: 'Marked At', render: (row) => (row.marked_at ? new Date(row.marked_at).toLocaleString() : '-') }
    ],
    [slotMap, studentMap]
  );

  return (
    <EntityManager
      title="Attendance Records"
      endpoint="/attendance-records/"
      createEndpoint="/attendance-records/mark"
      filters={filters}
      createFields={createFields}
      columns={columns}
      hideCreate={isStudent}
      enableDelete={false}
    />
  );
}
