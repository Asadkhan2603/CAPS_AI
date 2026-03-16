import { useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { searchLookupOptions } from '../services/paginatedLookups';

const OFFERING_TYPE_OPTIONS = [
  { value: 'theory', label: 'Theory' },
  { value: 'lab', label: 'Lab' },
  { value: 'elective', label: 'Elective' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'club', label: 'Club' },
  { value: 'interaction', label: 'Interaction' }
];

function mergeOptions(existing, next) {
  const merged = new Map((existing || []).map((item) => [String(item.value), item]));
  (next || []).forEach((item) => {
    merged.set(String(item.value), item);
  });
  return Array.from(merged.values());
}

export default function CourseOfferingsPage() {
  const [lookupState, setLookupState] = useState({
    subjects: [],
    teachers: [],
    batches: [],
    semesters: [],
    sections: [],
    groups: []
  });

  function rememberLookupOptions(key, options) {
    setLookupState((prev) => ({ ...prev, [key]: mergeOptions(prev[key], options) }));
    return options;
  }

  const subjectMap = useMemo(() => Object.fromEntries(lookupState.subjects.map((item) => [item.value, item.label])), [lookupState.subjects]);
  const teacherMap = useMemo(() => Object.fromEntries(lookupState.teachers.map((item) => [item.value, item.label])), [lookupState.teachers]);
  const batchMap = useMemo(() => Object.fromEntries(lookupState.batches.map((item) => [item.value, item.label])), [lookupState.batches]);
  const semesterMap = useMemo(() => Object.fromEntries(lookupState.semesters.map((item) => [item.value, item.label])), [lookupState.semesters]);
  const sectionMap = useMemo(() => Object.fromEntries(lookupState.sections.map((item) => [item.value, item.label])), [lookupState.sections]);
  const groupMap = useMemo(() => Object.fromEntries(lookupState.groups.map((item) => [item.value, item.label])), [lookupState.groups]);

  const loadSubjectOptions = async ({ query }) =>
    rememberLookupOptions(
      'subjects',
      await searchLookupOptions({
        path: '/subjects/',
        q: query,
        params: { is_active: true },
        mapOption: (item) => ({ value: item.id, label: `${item.name} (${item.code})` })
      })
    );

  const loadTeacherOptions = async ({ query }) =>
    rememberLookupOptions(
      'teachers',
      await searchLookupOptions({
        path: '/users/',
        q: query,
        params: { role: 'teacher', is_active: true, limit: 20 },
        mapOption: (item) => ({ value: item.id, label: `${item.full_name} (${item.email})` })
      })
    );

  const loadBatchOptions = async ({ query }) =>
    rememberLookupOptions(
      'batches',
      await searchLookupOptions({
        path: '/batches/',
        q: query,
        params: { is_active: true },
        mapOption: (item) => ({ value: item.id, label: `${item.name} (${item.code})` })
      })
    );

  const loadSemesterOptions = async ({ query, createValues, filterValues, mode }) => {
    const batchId = mode === 'create' ? createValues.batch_id : filterValues.batch_id;
    if (!batchId) return [];
    return rememberLookupOptions(
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
    return rememberLookupOptions(
      'sections',
      await searchLookupOptions({
        path: '/sections/',
        q: query,
        params: { batch_id: values.batch_id, semester_id: values.semester_id, is_active: true },
        mapOption: (item) => ({
          value: item.id,
          label: item.name,
          batch_id: item.batch_id,
          semester_id: item.semester_id
        })
      })
    );
  };

  const loadGroupOptions = async ({ query, createValues, filterValues, mode }) => {
    const sectionId = mode === 'create' ? createValues.section_id : filterValues.section_id;
    if (!sectionId) return [];
    return rememberLookupOptions(
      'groups',
      await searchLookupOptions({
        path: '/groups/',
        q: query,
        params: { section_id: sectionId, is_active: true },
        mapOption: (item) => ({
          value: item.id,
          label: `${item.name} (${item.code})`,
          section_id: item.section_id
        })
      })
    );
  };

  const filters = useMemo(
    () => [
      {
        name: 'batch_id',
        label: 'Batch',
        type: 'select',
        searchable: true,
        options: lookupState.batches,
        loadOptions: loadBatchOptions,
        selectedLabelResolver: ({ filterValues }) => batchMap[filterValues.batch_id] || '',
        placeholder: 'All Batches'
      },
      {
        name: 'semester_id',
        label: 'Semester',
        type: 'select',
        searchable: true,
        placeholder: 'All Semesters',
        loadOptions: loadSemesterOptions,
        selectedLabelResolver: ({ filterValues }) => semesterMap[filterValues.semester_id] || ''
      },
      {
        name: 'section_id',
        label: 'Section',
        type: 'select',
        searchable: true,
        placeholder: 'All Sections',
        loadOptions: loadSectionOptions,
        selectedLabelResolver: ({ filterValues }) => sectionMap[filterValues.section_id] || ''
      },
      {
        name: 'group_id',
        label: 'Group',
        type: 'select',
        searchable: true,
        placeholder: 'All Groups',
        loadOptions: loadGroupOptions,
        selectedLabelResolver: ({ filterValues }) => groupMap[filterValues.group_id] || ''
      },
      { name: 'academic_year', label: 'Academic Year' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [batchMap, groupMap, lookupState.batches, sectionMap, semesterMap]
  );

  const createFields = useMemo(
    () => [
      {
        name: 'subject_id',
        label: 'Subject',
        type: 'select',
        searchable: true,
        options: lookupState.subjects,
        loadOptions: loadSubjectOptions,
        selectedLabelResolver: ({ createValues }) => subjectMap[createValues.subject_id] || '',
        required: true
      },
      {
        name: 'teacher_user_id',
        label: 'Teacher',
        type: 'select',
        searchable: true,
        options: lookupState.teachers,
        loadOptions: loadTeacherOptions,
        selectedLabelResolver: ({ createValues }) => teacherMap[createValues.teacher_user_id] || '',
        required: true
      },
      {
        name: 'batch_id',
        label: 'Batch',
        type: 'select',
        searchable: true,
        options: lookupState.batches,
        loadOptions: loadBatchOptions,
        selectedLabelResolver: ({ createValues }) => batchMap[createValues.batch_id] || '',
        required: true
      },
      {
        name: 'semester_id',
        label: 'Semester',
        type: 'select',
        searchable: true,
        required: true,
        requireParentSelection: true,
        dependsOn: 'batch_id',
        placeholder: 'Select batch first',
        options: lookupState.semesters,
        loadOptions: loadSemesterOptions,
        selectedLabelResolver: ({ createValues }) => semesterMap[createValues.semester_id] || ''
      },
      {
        name: 'section_id',
        label: 'Section',
        type: 'select',
        searchable: true,
        required: true,
        requireParentSelection: true,
        dependsOn: 'semester_id',
        placeholder: 'Select semester first',
        options: lookupState.sections,
        loadOptions: loadSectionOptions,
        selectedLabelResolver: ({ createValues }) => sectionMap[createValues.section_id] || ''
      },
      {
        name: 'group_id',
        label: 'Group (Optional)',
        type: 'select',
        searchable: true,
        nullable: true,
        requireParentSelection: true,
        dependsOn: 'section_id',
        placeholder: 'Select section first',
        options: lookupState.groups,
        loadOptions: loadGroupOptions,
        selectedLabelResolver: ({ createValues }) => groupMap[createValues.group_id] || ''
      },
      { name: 'academic_year', label: 'Academic Year', required: true, defaultValue: '2025-26' },
      { name: 'offering_type', label: 'Delivery Type', type: 'select', options: OFFERING_TYPE_OPTIONS, required: true, defaultValue: 'theory' }
    ],
    [batchMap, groupMap, lookupState.batches, lookupState.groups, lookupState.sections, lookupState.semesters, lookupState.subjects, lookupState.teachers, sectionMap, semesterMap, subjectMap, teacherMap]
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
      { key: 'subject_id', label: 'Subject', render: (row) => subjectMap[row.subject_id] || row.subject_name || row.subject_id || '-' },
      { key: 'teacher_user_id', label: 'Teacher', render: (row) => teacherMap[row.teacher_user_id] || row.teacher_name || row.teacher_user_id || '-' },
      { key: 'section_id', label: 'Section', render: (row) => sectionMap[row.section_id] || row.section_name || row.section_id || '-' },
      { key: 'group_id', label: 'Group', render: (row) => groupMap[row.group_id] || row.group_name || '-' },
      { key: 'batch_id', label: 'Batch', render: (row) => batchMap[row.batch_id] || row.batch_name || row.batch_id || '-' },
      { key: 'semester_id', label: 'Semester', render: (row) => semesterMap[row.semester_id] || row.semester_label || row.semester_id || '-' },
      { key: 'academic_year', label: 'Year' },
      { key: 'offering_type', label: 'Delivery Type' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [batchMap, groupMap, sectionMap, semesterMap, subjectMap, teacherMap]
  );

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
        {'Course delivery follows one valid branch only: Batch -> Semester -> Section -> optional Group. The form narrows each dropdown so cross-branch offerings cannot be created.'}
      </div>
      <EntityManager
        title="Course Delivery"
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
    </div>
  );
}
