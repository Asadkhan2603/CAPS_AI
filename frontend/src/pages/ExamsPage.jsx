import { useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import EntityManager from '../components/ui/EntityManager';
import { useAuth } from '../hooks/useAuth';
import { searchLookupOptions } from '../services/paginatedLookups';

const EXAM_TYPE_OPTIONS = [
  { value: 'quiz', label: 'Quiz' },
  { value: 'midterm', label: 'Midterm' },
  { value: 'final', label: 'Final' },
  { value: 'practical', label: 'Practical' },
  { value: 'viva', label: 'Viva' },
  { value: 'internal', label: 'Internal' }
];

const STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' }
];

function mergeOptions(existing, next) {
  const merged = new Map((existing || []).map((item) => [String(item.value), item]));
  (next || []).forEach((item) => merged.set(String(item.value), item));
  return Array.from(merged.values());
}

export default function ExamsPage() {
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [lookupState, setLookupState] = useState({
    subjects: [],
    teachers: [],
    batches: [],
    semesters: [],
    sections: [],
    assignments: []
  });

  function remember(key, options) {
    setLookupState((prev) => ({ ...prev, [key]: mergeOptions(prev[key], options) }));
    return options;
  }

  const subjectMap = useMemo(() => Object.fromEntries(lookupState.subjects.map((item) => [item.value, item.label])), [lookupState.subjects]);
  const teacherMap = useMemo(() => Object.fromEntries(lookupState.teachers.map((item) => [item.value, item.label])), [lookupState.teachers]);
  const batchMap = useMemo(() => Object.fromEntries(lookupState.batches.map((item) => [item.value, item.label])), [lookupState.batches]);
  const semesterMap = useMemo(() => Object.fromEntries(lookupState.semesters.map((item) => [item.value, item.label])), [lookupState.semesters]);
  const sectionMap = useMemo(() => Object.fromEntries(lookupState.sections.map((item) => [item.value, item.label])), [lookupState.sections]);
  const assignmentMap = useMemo(() => Object.fromEntries(lookupState.assignments.map((item) => [item.value, item.label])), [lookupState.assignments]);

  const loadSubjectOptions = async ({ query }) =>
    remember(
      'subjects',
      await searchLookupOptions({
        path: '/subjects/',
        q: query,
        params: { is_active: true },
        mapOption: (item) => ({ value: item.id, label: `${item.name} (${item.code})` })
      })
    );

  const loadTeacherOptions = async ({ query }) =>
    remember(
      'teachers',
      await searchLookupOptions({
        path: '/users/',
        q: query,
        params: { role: 'teacher', is_active: true, limit: 20 },
        mapOption: (item) => ({ value: item.id, label: `${item.full_name} (${item.email})` })
      })
    );

  const loadBatchOptions = async ({ query }) =>
    remember(
      'batches',
      await searchLookupOptions({
        path: '/batches/',
        q: query,
        params: { is_active: true },
        mapOption: (item) => ({ value: item.id, label: item.name })
      })
    );

  const loadSemesterOptions = async ({ query, createValues, filterValues, mode }) => {
    const batchId = mode === 'create' ? createValues.batch_id : filterValues.batch_id;
    if (!batchId) return [];
    return remember(
      'semesters',
      await searchLookupOptions({
        path: '/semesters/',
        q: query,
        params: { is_active: true, batch_id: batchId },
        mapOption: (item) => ({ value: item.id, label: item.label, batch_id: item.batch_id })
      })
    );
  };

  const loadSectionOptions = async ({ query, createValues, filterValues, mode }) => {
    const values = mode === 'create' ? createValues : filterValues;
    if (!values.batch_id || !values.semester_id) return [];
    return remember(
      'sections',
      await searchLookupOptions({
        path: '/sections/',
        q: query,
        params: { batch_id: values.batch_id, semester_id: values.semester_id, is_active: true },
        mapOption: (item) => ({ value: item.id, label: item.name, batch_id: item.batch_id, semester_id: item.semester_id })
      })
    );
  };

  const loadAssignmentOptions = async ({ query, createValues, filterValues, mode }) => {
    const sectionId = mode === 'create' ? createValues.section_id : filterValues.section_id;
    return remember(
      'assignments',
      await searchLookupOptions({
        path: '/assignments/',
        q: query,
        params: { class_id: sectionId || undefined },
        mapOption: (item) => ({ value: item.id, label: item.title || item.display_label || item.id })
      })
    );
  };

  const filters = useMemo(
    () => [
      { name: 'batch_id', label: 'Batch', type: 'select', searchable: true, options: lookupState.batches, loadOptions: loadBatchOptions, selectedLabelResolver: ({ filterValues }) => batchMap[filterValues.batch_id] || '', placeholder: 'All Batches' },
      { name: 'semester_id', label: 'Semester', type: 'select', searchable: true, options: lookupState.semesters, loadOptions: loadSemesterOptions, selectedLabelResolver: ({ filterValues }) => semesterMap[filterValues.semester_id] || '', placeholder: 'All Semesters' },
      { name: 'section_id', label: 'Section', type: 'select', searchable: true, options: lookupState.sections, loadOptions: loadSectionOptions, selectedLabelResolver: ({ filterValues }) => sectionMap[filterValues.section_id] || '', placeholder: 'All Sections' },
      { name: 'subject_id', label: 'Subject', type: 'select', searchable: true, options: lookupState.subjects, loadOptions: loadSubjectOptions, selectedLabelResolver: ({ filterValues }) => subjectMap[filterValues.subject_id] || '', placeholder: 'All Subjects' },
      { name: 'status', label: 'Status', type: 'select', options: STATUS_OPTIONS, placeholder: 'All Statuses' }
    ],
    [batchMap, lookupState.batches, lookupState.sections, lookupState.semesters, lookupState.subjects, sectionMap, semesterMap, subjectMap]
  );

  const createFields = useMemo(
    () => [
      { name: 'title', label: 'Exam Title', required: true },
      { name: 'code', label: 'Exam Code', nullable: true },
      { name: 'description', label: 'Description', nullable: true },
      { name: 'subject_id', label: 'Subject', type: 'select', searchable: true, options: lookupState.subjects, loadOptions: loadSubjectOptions, selectedLabelResolver: ({ createValues }) => subjectMap[createValues.subject_id] || '', required: true },
      { name: 'teacher_user_id', label: 'Teacher', type: 'select', searchable: true, options: lookupState.teachers, loadOptions: loadTeacherOptions, selectedLabelResolver: ({ createValues }) => teacherMap[createValues.teacher_user_id] || '' },
      { name: 'batch_id', label: 'Batch', type: 'select', searchable: true, options: lookupState.batches, loadOptions: loadBatchOptions, selectedLabelResolver: ({ createValues }) => batchMap[createValues.batch_id] || '', required: true },
      { name: 'semester_id', label: 'Semester', type: 'select', searchable: true, options: lookupState.semesters, loadOptions: loadSemesterOptions, selectedLabelResolver: ({ createValues }) => semesterMap[createValues.semester_id] || '', required: true, requireParentSelection: true, dependsOn: 'batch_id', placeholder: 'Select batch first' },
      { name: 'section_id', label: 'Section', type: 'select', searchable: true, options: lookupState.sections, loadOptions: loadSectionOptions, selectedLabelResolver: ({ createValues }) => sectionMap[createValues.section_id] || '', required: true, requireParentSelection: true, dependsOn: 'semester_id', placeholder: 'Select semester first' },
      { name: 'assignment_id', label: 'Linked Assignment', type: 'select', searchable: true, options: lookupState.assignments, loadOptions: loadAssignmentOptions, selectedLabelResolver: ({ createValues }) => assignmentMap[createValues.assignment_id] || '', nullable: true },
      { name: 'exam_type', label: 'Exam Type', type: 'select', options: EXAM_TYPE_OPTIONS, required: true, defaultValue: 'internal' },
      { name: 'scheduled_for', label: 'Scheduled At', type: 'datetime-local', nullable: true },
      { name: 'duration_minutes', label: 'Duration (minutes)', type: 'number', required: true, defaultValue: 60 },
      { name: 'room_code', label: 'Room', nullable: true },
      { name: 'max_marks', label: 'Max Marks', type: 'number', required: true, defaultValue: 100 },
      { name: 'status', label: 'Status', type: 'select', options: STATUS_OPTIONS, required: true, defaultValue: 'draft' }
    ],
    [assignmentMap, batchMap, lookupState.assignments, lookupState.batches, lookupState.sections, lookupState.semesters, lookupState.subjects, lookupState.teachers, sectionMap, semesterMap, subjectMap, teacherMap]
  );

  const editFields = useMemo(() => [...createFields, { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true }], [createFields]);

  const columns = useMemo(
    () => [
      { key: 'title', label: 'Exam' },
      { key: 'code', label: 'Code' },
      { key: 'subject_id', label: 'Subject', render: (row) => subjectMap[row.subject_id] || row.subject_id || '-' },
      { key: 'section_id', label: 'Section', render: (row) => sectionMap[row.section_id] || row.section_id || '-' },
      { key: 'teacher_user_id', label: 'Teacher', render: (row) => teacherMap[row.teacher_user_id] || row.teacher_user_id || '-' },
      { key: 'exam_type', label: 'Type' },
      { key: 'scheduled_for', label: 'Scheduled', render: (row) => (row.scheduled_for ? new Date(row.scheduled_for).toLocaleString() : '-') },
      { key: 'room_code', label: 'Room' },
      { key: 'status', label: 'Status' }
    ],
    [sectionMap, subjectMap, teacherMap]
  );

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <h1 className="text-2xl font-semibold">{isStudent ? 'My Exams' : 'Exams'}</h1>
        <p className="text-sm text-slate-500">
          {isStudent
            ? 'View your formal exam schedule, linked subject context, and published room timing details.'
            : 'Exam-core workspace for formal exam definition, scheduling, and subject-section mapping.'}
        </p>
      </Card>
      <EntityManager
        title={isStudent ? 'My Exams' : 'Exams'}
        endpoint="/exams/"
        filters={filters}
        createFields={createFields}
        editFields={editFields}
        columns={columns}
        enableEdit={!isStudent}
        enableDelete={!isStudent}
        hideCreate={isStudent}
        createTransform={(payload) => ({
          ...payload,
          code: payload.code || null,
          description: payload.description || null,
          teacher_user_id: payload.teacher_user_id || null,
          assignment_id: payload.assignment_id || null,
          room_code: payload.room_code || null,
          scheduled_for: payload.scheduled_for || null
        })}
        updateTransform={(payload) => ({
          ...payload,
          code: payload.code || null,
          description: payload.description || null,
          teacher_user_id: payload.teacher_user_id || null,
          assignment_id: payload.assignment_id || null,
          room_code: payload.room_code || null,
          scheduled_for: payload.scheduled_for || null
        })}
      />
    </div>
  );
}
