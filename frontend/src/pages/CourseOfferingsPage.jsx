import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { searchLookupOptions } from '../services/paginatedLookups';
import { getSectionDashboard } from '../services/sectionsApi';

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
  const [dashboard, setDashboard] = useState(null);
  const [activeOfferings, setActiveOfferings] = useState([]);
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

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [dashboardResponse, offeringsResponse] = await Promise.all([
          getSectionDashboard(),
          apiClient.get('/course-offerings/', { params: { skip: 0, limit: 200, is_active: true } })
        ]);
        setDashboard(dashboardResponse || null);
        setActiveOfferings(offeringsResponse.data || []);
      } catch {
        setDashboard(null);
        setActiveOfferings([]);
      }
    }
    loadDashboard();
  }, []);

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

  const setupPrioritySections = useMemo(() => {
    const items = [...(dashboard?.sections || [])];
    return items
      .filter(
        (item) =>
          item.active_offering_count === 0 ||
          item.latest_timetable_drift_count > 0 ||
          item.unreleased_evaluation_count > 0
      )
      .sort((left, right) => {
        const leftScore =
          (left.active_offering_count === 0 ? 20 : 0) +
          (left.latest_timetable_drift_count || 0) * 8 +
          (left.unreleased_evaluation_count || 0) * 4;
        const rightScore =
          (right.active_offering_count === 0 ? 20 : 0) +
          (right.latest_timetable_drift_count || 0) * 8 +
          (right.unreleased_evaluation_count || 0) * 4;
        return rightScore - leftScore;
      })
      .slice(0, 5);
  }, [dashboard]);

  const teacherLoadSummary = useMemo(() => {
    const buckets = new Map();
    for (const offering of activeOfferings) {
      const teacherId = offering.teacher_user_id || '';
      if (!teacherId) continue;
      const bucket = buckets.get(teacherId) || {
        teacher_user_id: teacherId,
        teacher_name: teacherMap[teacherId] || offering.teacher_name || teacherId,
        offering_count: 0,
        section_ids: new Set(),
        theory_count: 0,
        lab_count: 0,
      };
      bucket.offering_count += 1;
      if (offering.section_id) bucket.section_ids.add(offering.section_id);
      if (offering.offering_type === 'lab') bucket.lab_count += 1;
      else bucket.theory_count += 1;
      buckets.set(teacherId, bucket);
    }
    return Array.from(buckets.values())
      .map((item) => ({
        ...item,
        section_count: item.section_ids.size,
      }))
      .sort((left, right) => right.offering_count - left.offering_count)
      .slice(0, 6);
  }, [activeOfferings, teacherMap]);

  const sectionCapacitySummary = useMemo(() => {
    const sections = dashboard?.sections || [];
    return sections
      .map((item) => {
        const studentCount = Number(item.student_count || 0);
        const offeringCount = Number(item.active_offering_count || 0);
        const studentsPerOffering = offeringCount ? Math.round(studentCount / offeringCount) : studentCount;
        const pressure = offeringCount === 0 ? 'Critical' : studentsPerOffering >= 35 ? 'High' : studentsPerOffering >= 25 ? 'Medium' : 'Balanced';
        return {
          section_id: item.section_id,
          section_name: item.section_name,
          student_count: studentCount,
          offering_count: offeringCount,
          students_per_offering: studentsPerOffering,
          pressure,
        };
      })
      .sort((left, right) => {
        const rank = { Critical: 3, High: 2, Medium: 1, Balanced: 0 };
        return rank[right.pressure] - rank[left.pressure] || right.students_per_offering - left.students_per_offering;
      })
      .slice(0, 6);
  }, [dashboard]);

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
        {'Course delivery follows one valid branch only: Batch -> Semester -> Section -> optional Group. The form narrows each dropdown so cross-branch offerings cannot be created.'}
      </div>
      {dashboard ? (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ['Active Offerings', dashboard.total_active_offerings || 0],
              ['Sections With No Offerings', (dashboard.sections || []).filter((item) => item.active_offering_count === 0).length],
              ['Sections With Timetable Drift', dashboard.sections_with_drift || 0],
              ['Sections With Unreleased Results', (dashboard.sections || []).filter((item) => item.unreleased_evaluation_count > 0).length]
            ].map(([label, value]) => (
              <Card key={label} className="!p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </Card>
            ))}
          </div>
          <div className="grid gap-3 xl:grid-cols-[0.95fr_1.05fr]">
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Course Delivery Setup Guide</h2>
                <p className="text-sm text-slate-500">
                  Keep setup in one safe branch: subject and teacher first, then batch, semester, section, and optional group.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ['1. Start with batch', 'Batch narrows semesters and keeps the delivery inside one academic branch.'],
                  ['2. Confirm section coverage', 'Use the section summary cards to spot sections with no offerings before adding more records.'],
                  ['3. Check downstream pressure', 'If drift or unreleased results are high, fix those sections before expanding delivery.']
                ].map(([title, body]) => (
                  <div key={title} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                    <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
                    <p className="mt-2 text-sm text-slate-600">{body}</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Setup Priorities</h2>
                <p className="text-sm text-slate-500">
                  Sections shown here need offering setup, timetable cleanup, or result-release follow-through.
                </p>
              </div>
              <div className="space-y-3">
                {setupPrioritySections.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                    No delivery setup priorities detected in the current scope.
                  </div>
                ) : (
                  setupPrioritySections.map((item) => (
                    <div key={item.section_id} className="rounded-2xl border border-slate-200 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-medium text-slate-900">{item.section_name}</h3>
                          <p className="text-sm text-slate-500">
                            {item.student_count} students • {item.active_offering_count} offerings
                          </p>
                        </div>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                          {item.latest_timetable_sync_status || item.latest_timetable_status || 'No timetable'}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs">
                        {item.active_offering_count === 0 ? (
                          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">No offerings</span>
                        ) : null}
                        <span className="rounded-full bg-rose-50 px-2.5 py-1 text-rose-700">
                          Drift {item.latest_timetable_drift_count || 0}
                        </span>
                        <span className="rounded-full bg-sky-50 px-2.5 py-1 text-sky-700">
                          Unreleased {item.unreleased_evaluation_count || 0}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
          <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Teacher Load Summary</h2>
                <p className="text-sm text-slate-500">
                  Use this before adding more offerings so one teacher does not silently absorb too many sections.
                </p>
              </div>
              <div className="space-y-3">
                {teacherLoadSummary.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                    No active offerings available for teacher load analysis.
                  </div>
                ) : (
                  teacherLoadSummary.map((item) => (
                    <div key={item.teacher_user_id} className="rounded-2xl border border-slate-200 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-medium text-slate-900">{item.teacher_name}</h3>
                          <p className="text-sm text-slate-500">
                            {item.offering_count} offerings • {item.section_count} sections
                          </p>
                        </div>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                          {item.lab_count} lab / {item.theory_count} non-lab
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Section Capacity Pressure</h2>
                <p className="text-sm text-slate-500">
                  Students per active offering gives a quick proxy for sections that may need more delivery coverage.
                </p>
              </div>
              <div className="space-y-3">
                {sectionCapacitySummary.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                    No sections available for capacity analysis.
                  </div>
                ) : (
                  sectionCapacitySummary.map((item) => (
                    <div key={item.section_id} className="rounded-2xl border border-slate-200 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-medium text-slate-900">{item.section_name}</h3>
                          <p className="text-sm text-slate-500">
                            {item.student_count} students • {item.offering_count} offerings
                          </p>
                        </div>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          item.pressure === 'Critical'
                            ? 'bg-rose-50 text-rose-700'
                            : item.pressure === 'High'
                              ? 'bg-amber-50 text-amber-700'
                              : item.pressure === 'Medium'
                                ? 'bg-sky-50 text-sky-700'
                                : 'bg-emerald-50 text-emerald-700'
                        }`}>
                          {item.pressure}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-slate-600">
                        Students per offering: {item.students_per_offering}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>
      ) : null}
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
