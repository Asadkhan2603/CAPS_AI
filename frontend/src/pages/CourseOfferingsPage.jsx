import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { getAllSections } from '../services/sectionsApi';

const OFFERING_TYPE_OPTIONS = [
  { value: 'theory', label: 'Theory' },
  { value: 'lab', label: 'Lab' },
  { value: 'elective', label: 'Elective' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'club', label: 'Club' },
  { value: 'interaction', label: 'Interaction' }
];

export default function CourseOfferingsPage() {
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [sections, setSections] = useState([]);
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    async function loadLookups() {
      const [subjectsRes, usersRes, batchesRes, semestersRes, groupsRes] = await Promise.allSettled([
        apiClient.get('/subjects/', { params: { skip: 0, limit: 300 } }),
        apiClient.get('/users/'),
        apiClient.get('/batches/', { params: { skip: 0, limit: 300 } }),
        apiClient.get('/semesters/', { params: { skip: 0, limit: 300 } }),
        apiClient.get('/groups/', { params: { skip: 0, limit: 300 } })
      ]);
      setSubjects(subjectsRes.status === 'fulfilled' ? subjectsRes.value.data || [] : []);
      setTeachers(
        usersRes.status === 'fulfilled' ? (usersRes.value.data || []).filter((item) => item.role === 'teacher' || item.role === 'admin') : []
      );
      setBatches(batchesRes.status === 'fulfilled' ? batchesRes.value.data || [] : []);
      setSemesters(semestersRes.status === 'fulfilled' ? semestersRes.value.data || [] : []);
      setGroups(groupsRes.status === 'fulfilled' ? groupsRes.value.data || [] : []);
      try {
        const sectionRows = await getAllSections(100);
        setSections(sectionRows || []);
      } catch {
        setSections([]);
      }
    }
    loadLookups();
  }, []);

  const subjectOptions = useMemo(() => subjects.map((item) => ({ value: item.id, label: `${item.name} (${item.code})` })), [subjects]);
  const teacherOptions = useMemo(() => teachers.map((item) => ({ value: item.id, label: `${item.full_name} (${item.email})` })), [teachers]);
  const batchOptions = useMemo(() => batches.map((item) => ({ value: item.id, label: `${item.name} (${item.code})` })), [batches]);
  const semesterOptions = useMemo(() => semesters.map((item) => ({ value: item.id, label: item.label })), [semesters]);
  const sectionOptions = useMemo(() => sections.map((item) => ({ value: item.id, label: item.name })), [sections]);
  const groupOptions = useMemo(() => groups.map((item) => ({ value: item.id, label: `${item.name} (${item.code})` })), [groups]);

  const subjectMap = useMemo(() => Object.fromEntries(subjects.map((item) => [item.id, `${item.name} (${item.code})`])), [subjects]);
  const teacherMap = useMemo(() => Object.fromEntries(teachers.map((item) => [item.id, item.full_name])), [teachers]);
  const batchMap = useMemo(() => Object.fromEntries(batches.map((item) => [item.id, item.name])), [batches]);
  const semesterMap = useMemo(() => Object.fromEntries(semesters.map((item) => [item.id, item.label])), [semesters]);
  const sectionMap = useMemo(() => Object.fromEntries(sections.map((item) => [item.id, item.name])), [sections]);
  const groupMap = useMemo(() => Object.fromEntries(groups.map((item) => [item.id, item.name])), [groups]);

  const filters = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'semester_id', label: 'Semester', type: 'select', options: semesterOptions, placeholder: 'All Semesters' },
      { name: 'group_id', label: 'Group', type: 'select', options: groupOptions, placeholder: 'All Groups' },
      { name: 'academic_year', label: 'Academic Year' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [groupOptions, sectionOptions, semesterOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'subject_id', label: 'Subject', type: 'select', options: subjectOptions, required: true },
      { name: 'teacher_user_id', label: 'Teacher', type: 'select', options: teacherOptions, required: true },
      { name: 'batch_id', label: 'Batch', type: 'select', options: batchOptions, required: true },
      { name: 'semester_id', label: 'Semester', type: 'select', options: semesterOptions, required: true },
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, required: true },
      { name: 'group_id', label: 'Group (Optional)', type: 'select', options: groupOptions, nullable: true },
      { name: 'academic_year', label: 'Academic Year', required: true, defaultValue: '2025-26' },
      { name: 'offering_type', label: 'Offering Type', type: 'select', options: OFFERING_TYPE_OPTIONS, required: true, defaultValue: 'theory' }
    ],
    [batchOptions, groupOptions, sectionOptions, semesterOptions, subjectOptions, teacherOptions]
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
      { key: 'subject_id', label: 'Subject', render: (row) => subjectMap[row.subject_id] || row.subject_id || '-' },
      { key: 'teacher_user_id', label: 'Teacher', render: (row) => teacherMap[row.teacher_user_id] || row.teacher_user_id || '-' },
      { key: 'section_id', label: 'Section', render: (row) => sectionMap[row.section_id] || row.section_id || '-' },
      { key: 'group_id', label: 'Group', render: (row) => groupMap[row.group_id] || '-' },
      { key: 'batch_id', label: 'Batch', render: (row) => batchMap[row.batch_id] || row.batch_id || '-' },
      { key: 'semester_id', label: 'Semester', render: (row) => semesterMap[row.semester_id] || row.semester_id || '-' },
      { key: 'academic_year', label: 'Year' },
      { key: 'offering_type', label: 'Type' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [batchMap, groupMap, sectionMap, semesterMap, subjectMap, teacherMap]
  );

  return (
    <EntityManager
      title="Course Offerings"
      endpoint="/course-offerings/"
      filters={filters}
      createFields={createFields}
      editFields={editFields}
      columns={columns}
      enableEdit
      enableDelete
      createTransform={(payload) => ({ ...payload, group_id: payload.group_id || null })}
      updateTransform={(payload) => ({ ...payload, group_id: payload.group_id || null })}
    />
  );
}
