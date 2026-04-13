import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import SearchableSelect from '../components/ui/SearchableSelect';
import Table from '../components/ui/Table';
import { createSection, getSectionDashboard, getSections, syncSectionGroups } from '../services/sectionsApi';
import { searchLookupOptions } from '../services/paginatedLookups';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';

export default function SectionsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const { pushToast } = useToast();

  const [rows, setRows] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [teachers, setTeachers] = useState([]);

  const [loading, setLoading] = useState(false);
  const [syncingGroups, setSyncingGroups] = useState(false);
  const [error, setError] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);

  const [filters, setFilters] = useState({
    faculty_id: '',
    department_id: '',
    program_id: '',
    specialization_id: '',
    batch_id: '',
    semester_id: ''
  });

  const [form, setForm] = useState({
    faculty_id: '',
    department_id: '',
    program_id: '',
    specialization_id: '',
    batch_id: '',
    semester_id: '',
    name: '',
    class_coordinator_user_id: ''
  });

  function updateFilters(updater) {
    setSkip(0);
    setFilters((prev) => (typeof updater === 'function' ? updater(prev) : { ...prev, ...updater }));
  }

  const facultyNameById = useMemo(() => Object.fromEntries(faculties.map((item) => [item.id, item.name])), [faculties]);
  const departmentNameById = useMemo(() => Object.fromEntries(departments.map((item) => [item.id, item.name])), [departments]);
  const programNameById = useMemo(() => Object.fromEntries(programs.map((item) => [item.id, item.name])), [programs]);
  const specializationNameById = useMemo(
    () => Object.fromEntries(specializations.map((item) => [item.id, item.name])),
    [specializations]
  );
  const batchById = useMemo(() => Object.fromEntries(batches.map((item) => [item.id, item])), [batches]);
  const batchNameById = useMemo(() => Object.fromEntries(batches.map((item) => [item.id, item.name])), [batches]);
  const semesterLabelById = useMemo(() => Object.fromEntries(semesters.map((item) => [item.id, item.label])), [semesters]);
  const teacherNameById = useMemo(() => Object.fromEntries(teachers.map((item) => [item.id, item.full_name])), [teachers]);

  const selectedFormBatch = form.batch_id ? batchById[form.batch_id] || null : null;
  const selectedFilterBatch = filters.batch_id ? batchById[filters.batch_id] || null : null;
  const formBatchSpecializationId = selectedFormBatch?.specialization_id || '';
  const filterBatchSpecializationId = selectedFilterBatch?.specialization_id || '';

  const availableDepartmentsForForm = useMemo(
    () => departments.filter((item) => !form.faculty_id || item.faculty_id === form.faculty_id),
    [departments, form.faculty_id]
  );
  const availableProgramsForForm = useMemo(
    () => programs.filter((item) => !form.department_id || item.department_id === form.department_id),
    [programs, form.department_id]
  );
  const availableSpecializationsForForm = useMemo(
    () => {
      if (formBatchSpecializationId) {
        return specializations.filter((item) => item.id === formBatchSpecializationId);
      }
      if (selectedFormBatch && !selectedFormBatch.specialization_id) {
        return [];
      }
      return specializations.filter((item) => !form.program_id || item.program_id === form.program_id);
    },
    [form.program_id, formBatchSpecializationId, selectedFormBatch, specializations]
  );
  const availableBatchesForForm = useMemo(
    () =>
      batches.filter(
        (item) =>
          (!form.program_id || item.program_id === form.program_id) &&
          (!form.specialization_id || item.specialization_id === form.specialization_id)
      ),
    [batches, form.program_id, form.specialization_id]
  );
  const availableSemestersForForm = useMemo(
    () => semesters.filter((item) => !form.batch_id || item.batch_id === form.batch_id),
    [semesters, form.batch_id]
  );

  const availableDepartmentsForFilters = useMemo(
    () => departments.filter((item) => !filters.faculty_id || item.faculty_id === filters.faculty_id),
    [departments, filters.faculty_id]
  );
  const availableProgramsForFilters = useMemo(
    () => programs.filter((item) => !filters.department_id || item.department_id === filters.department_id),
    [programs, filters.department_id]
  );
  const availableSpecializationsForFilters = useMemo(
    () => {
      if (filterBatchSpecializationId) {
        return specializations.filter((item) => item.id === filterBatchSpecializationId);
      }
      if (selectedFilterBatch && !selectedFilterBatch.specialization_id) {
        return [];
      }
      return specializations.filter((item) => !filters.program_id || item.program_id === filters.program_id);
    },
    [filterBatchSpecializationId, filters.program_id, selectedFilterBatch, specializations]
  );
  const availableBatchesForFilters = useMemo(
    () =>
      batches.filter(
        (item) =>
          (!filters.program_id || item.program_id === filters.program_id) &&
          (!filters.specialization_id || item.specialization_id === filters.specialization_id)
      ),
    [batches, filters.program_id, filters.specialization_id]
  );
  const availableSemestersForFilters = useMemo(
    () => semesters.filter((item) => !filters.batch_id || item.batch_id === filters.batch_id),
    [semesters, filters.batch_id]
  );

  function mergeRows(setter, rows) {
    setter((prev) => {
      const merged = new Map((prev || []).map((item) => [String(item.id), item]));
      (rows || []).forEach((item) => {
        if (item?.id) {
          merged.set(String(item.id), item);
        }
      });
      return Array.from(merged.values());
    });
  }

  async function loadFacultyOptions(query) {
    const options = await searchLookupOptions({
      path: '/faculties/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({ value: item.id, label: item.name })
    });
    mergeRows(setFaculties, options.map((item) => ({ id: item.value, name: item.label })));
    return options;
  }

  async function loadDepartmentOptions(query, facultyId) {
    if (!facultyId) return [];
    const options = await searchLookupOptions({
      path: '/departments/',
      q: query,
      params: { is_active: true, faculty_id: facultyId },
      mapOption: (item) => ({ value: item.id, label: item.name, faculty_id: item.faculty_id })
    });
    mergeRows(setDepartments, options.map((item) => ({ id: item.value, name: item.label, faculty_id: item.faculty_id })));
    return options;
  }

  async function loadProgramOptions(query, departmentId) {
    if (!departmentId) return [];
    const options = await searchLookupOptions({
      path: '/programs/',
      q: query,
      params: { is_active: true, department_id: departmentId },
      mapOption: (item) => ({ value: item.id, label: item.name, department_id: item.department_id })
    });
    mergeRows(setPrograms, options.map((item) => ({ id: item.value, name: item.label, department_id: item.department_id })));
    return options;
  }

  async function loadSpecializationOptions(query, programId) {
    if (!programId) return [];
    const options = await searchLookupOptions({
      path: '/specializations/',
      q: query,
      params: { is_active: true, program_id: programId },
      mapOption: (item) => ({ value: item.id, label: item.name, program_id: item.program_id })
    });
    mergeRows(setSpecializations, options.map((item) => ({ id: item.value, name: item.label, program_id: item.program_id })));
    return options;
  }

  async function loadBatchOptions(query, programId, specializationId) {
    if (!programId) return [];
    const options = await searchLookupOptions({
      path: '/batches/',
      q: query,
      params: { is_active: true, program_id: programId, specialization_id: specializationId || undefined },
      mapOption: (item) => ({
        value: item.id,
        label: item.name,
        program_id: item.program_id,
        specialization_id: item.specialization_id
      })
    });
    mergeRows(
      setBatches,
      options.map((item) => ({
        id: item.value,
        name: item.label,
        program_id: item.program_id,
        specialization_id: item.specialization_id
      }))
    );
    return options;
  }

  async function loadSemesterOptions(query, batchId) {
    if (!batchId) return [];
    const options = await searchLookupOptions({
      path: '/semesters/',
      q: query,
      params: { is_active: true, batch_id: batchId },
      mapOption: (item) => ({ value: item.id, label: item.label, batch_id: item.batch_id })
    });
    mergeRows(setSemesters, options.map((item) => ({ id: item.value, label: item.label, batch_id: item.batch_id })));
    return options;
  }

  async function loadTeacherOptions(query) {
    if (!isAdmin) return [];
    const options = await searchLookupOptions({
      path: '/users/',
      q: query,
      params: { role: 'teacher', is_active: true, limit: 20 },
      mapOption: (item) => ({ value: item.id, label: `${item.full_name} (${item.email})`, full_name: item.full_name })
    });
    mergeRows(
      setTeachers,
      options.map((item) => ({ id: item.value, full_name: item.full_name || item.label }))
    );
    return options;
  }

  async function loadSections() {
    setLoading(true);
    setError('');
    try {
      const response = await getSections({
        faculty_id: filters.faculty_id || undefined,
        department_id: filters.department_id || undefined,
        program_id: filters.program_id || undefined,
        specialization_id: filters.specialization_id || undefined,
        batch_id: filters.batch_id || undefined,
        semester_id: filters.semester_id || undefined,
        skip,
        limit
      });
      setRows(response.data || []);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load sections');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  async function loadDashboard() {
    try {
      const response = await getSectionDashboard({
        faculty_id: filters.faculty_id || undefined,
        department_id: filters.department_id || undefined,
        program_id: filters.program_id || undefined,
        specialization_id: filters.specialization_id || undefined,
        batch_id: filters.batch_id || undefined,
        semester_id: filters.semester_id || undefined
      });
      setDashboard(response || null);
    } catch {
      setDashboard(null);
    }
  }

  useEffect(() => {
    loadSections();
    loadDashboard();
  }, [skip, limit, filters]);

  function handleFormBatchChange(batchId) {
    const nextBatch = batchId ? batchById[batchId] || null : null;
    setForm((prev) => ({
      ...prev,
      batch_id: batchId,
      semester_id: '',
      specialization_id: nextBatch?.specialization_id || ''
    }));
  }

  function handleFilterBatchChange(batchId) {
    const nextBatch = batchId ? batchById[batchId] || null : null;
    setFilters((prev) => ({
      ...prev,
      batch_id: batchId,
      semester_id: '',
      specialization_id: nextBatch?.specialization_id || ''
    }));
  }

  async function onCreate(event) {
    event.preventDefault();
    try {
      await createSection({
        faculty_id: form.faculty_id || null,
        department_id: form.department_id || null,
        program_id: form.program_id || null,
        specialization_id: form.specialization_id || null,
        batch_id: form.batch_id || null,
        semester_id: form.semester_id || null,
        name: form.name,
        class_coordinator_user_id: form.class_coordinator_user_id || null,
        faculty_name: facultyNameById[form.faculty_id] || null
      });
      pushToast({ title: 'Created', description: 'Section created successfully.', variant: 'success' });
      setForm({
        faculty_id: '',
        department_id: '',
        program_id: '',
        specialization_id: '',
        batch_id: '',
        semester_id: '',
        name: '',
        class_coordinator_user_id: ''
      });
      setSkip(0);
      await loadSections();
    } catch (err) {
      const message = formatApiError(err, 'Failed to create section');
      setError(message);
      pushToast({ title: 'Create failed', description: message, variant: 'error' });
    }
  }

  async function onSyncGroups() {
    setSyncingGroups(true);
    try {
      const response = await syncSectionGroups();
      const payload = response?.data || {};
      pushToast({
        title: 'Groups synced',
        description: `${payload.created ?? 0} created, ${payload.reactivated ?? 0} reactivated, ${payload.updated ?? 0} updated across ${payload.section_count ?? 0} sections.`,
        variant: 'success'
      });
    } catch (err) {
      const message = formatApiError(err, 'Failed to sync section groups');
      setError(message);
      pushToast({ title: 'Sync failed', description: message, variant: 'error' });
    } finally {
      setSyncingGroups(false);
    }
  }

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Section' },
      { key: 'faculty_id', label: 'Faculty', render: (row) => row.faculty_name || facultyNameById[row.faculty_id] || '-' },
      { key: 'department_id', label: 'Department', render: (row) => row.department_name || departmentNameById[row.department_id] || '-' },
      { key: 'program_id', label: 'Program', render: (row) => row.program_name || programNameById[row.program_id] || '-' },
      {
        key: 'specialization_id',
        label: 'Specialization',
        render: (row) => row.specialization_name || specializationNameById[row.specialization_id] || '-'
      },
      { key: 'batch_id', label: 'Batch', render: (row) => row.batch_name || batchNameById[row.batch_id] || '-' },
      { key: 'semester_id', label: 'Semester', render: (row) => row.semester_label || semesterLabelById[row.semester_id] || '-' },
      {
        key: 'class_coordinator_user_id',
        label: 'Coordinator',
        render: (row) =>
          row.class_coordinator_user_id
            ? row.class_coordinator_name || teacherNameById[row.class_coordinator_user_id] || row.class_coordinator_user_id
            : '-'
      }
    ],
    [
      batchNameById,
      departmentNameById,
      facultyNameById,
      programNameById,
      semesterLabelById,
      specializationNameById,
      teacherNameById
    ]
  );

  const sectionHealthColumns = useMemo(
    () => [
      { key: 'section_name', label: 'Section' },
      { key: 'student_count', label: 'Students' },
      { key: 'active_offering_count', label: 'Offerings' },
      { key: 'average_attendance_percent', label: 'Attendance', render: (row) => (row.average_attendance_percent != null ? `${row.average_attendance_percent}%` : '-') },
      { key: 'latest_timetable_sync_status', label: 'Timetable Sync', render: (row) => row.latest_timetable_sync_status || row.latest_timetable_status || '-' },
      { key: 'latest_timetable_drift_count', label: 'Drift' },
      { key: 'unreleased_evaluation_count', label: 'Unreleased Results' }
    ],
    []
  );

  const prioritySections = useMemo(() => {
    const items = [...(dashboard?.sections || [])];
    return items
      .sort((left, right) => {
        const leftScore =
          (left.latest_timetable_drift_count || 0) * 10 +
          (left.unreleased_evaluation_count || 0) * 4 +
          (left.shortage_risk_count || 0) * 6;
        const rightScore =
          (right.latest_timetable_drift_count || 0) * 10 +
          (right.unreleased_evaluation_count || 0) * 4 +
          (right.shortage_risk_count || 0) * 6;
        return rightScore - leftScore;
      })
      .slice(0, 4);
  }, [dashboard]);

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Sections</h1>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" onClick={onSyncGroups} disabled={syncingGroups}>
              {syncingGroups ? 'Syncing Groups...' : 'Sync Groups'}
            </button>
            <button className="btn-secondary" onClick={() => { setSkip(0); loadSections(); }}>Refresh</button>
          </div>
        </div>
        <p className="text-sm text-slate-500">
          Section operations now surface delivery health, timetable trust, attendance coverage, and result-release pressure so coordinators can spot problems before editing structure.
        </p>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <SearchableSelect
            label="Faculty"
            value={filters.faculty_id}
            loadKey="sections-filter-faculty"
            options={faculties.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={loadFacultyOptions}
            selectedLabel={facultyNameById[filters.faculty_id] || ''}
            allowEmpty
            emptyLabel="All Faculties"
            placeholder="Search faculty"
            onValueChange={(value) =>
              updateFilters((prev) => ({
                ...prev,
                faculty_id: value,
                department_id: '',
                program_id: '',
                specialization_id: '',
                batch_id: '',
                semester_id: ''
              }))
            }
          />
          <SearchableSelect
            label="Department"
            value={filters.department_id}
            loadKey={`sections-filter-department:${filters.faculty_id || ''}`}
            options={availableDepartmentsForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadDepartmentOptions(query, filters.faculty_id)}
            selectedLabel={departmentNameById[filters.department_id] || ''}
            allowEmpty
            disabled={!filters.faculty_id}
            emptyLabel="All Departments"
            placeholder={filters.faculty_id ? 'Search department' : 'Select faculty first'}
            onValueChange={(value) =>
              updateFilters((prev) => ({
                ...prev,
                department_id: value,
                program_id: '',
                specialization_id: '',
                batch_id: '',
                semester_id: ''
              }))
            }
          />
          <SearchableSelect
            label="Program"
            value={filters.program_id}
            loadKey={`sections-filter-program:${filters.department_id || ''}`}
            options={availableProgramsForFilters.map((item) => ({ value: item.id, label: item.name }))} 
            loadOptions={(query) => loadProgramOptions(query, filters.department_id)}
            selectedLabel={programNameById[filters.program_id] || ''}
            allowEmpty
            disabled={!filters.department_id}
            emptyLabel="All Programs"
            placeholder={filters.department_id ? 'Search program' : 'Select department first'}
            onValueChange={(value) =>
              updateFilters((prev) => ({
                ...prev,
                program_id: value,
                specialization_id: '',
                batch_id: '',
                semester_id: ''
              }))
            }
          />
          <SearchableSelect
            label="Specialization"
            value={filters.specialization_id}
            loadKey={`sections-filter-specialization:${filters.program_id || ''}`}
            options={availableSpecializationsForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadSpecializationOptions(query, filters.program_id)}
            selectedLabel={specializationNameById[filters.specialization_id] || ''}
            allowEmpty
            disabled={Boolean(selectedFilterBatch) || !filters.program_id}
            emptyLabel={
              selectedFilterBatch
                ? selectedFilterBatch.specialization_id
                  ? 'Batch specialization'
                  : 'Program-level batch'
                : 'All Specializations'
            }
            placeholder={filters.program_id ? 'Search specialization' : 'Select program first'}
            onValueChange={(value) =>
              updateFilters((prev) => ({
                ...prev,
                specialization_id: value,
                batch_id: '',
                semester_id: ''
              }))
            }
          />
          <SearchableSelect
            label="Batch"
            value={filters.batch_id}
            loadKey={`sections-filter-batch:${filters.program_id || ''}:${filters.specialization_id || ''}`}
            options={availableBatchesForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadBatchOptions(query, filters.program_id, filters.specialization_id)}
            selectedLabel={batchNameById[filters.batch_id] || ''}
            allowEmpty
            disabled={!filters.program_id}
            emptyLabel="All Batches"
            placeholder={filters.program_id ? 'Search batch' : 'Select program first'}
            onValueChange={(value) => {
              setSkip(0);
              handleFilterBatchChange(value);
            }}
          />
          <SearchableSelect
            label="Semester"
            value={filters.semester_id}
            loadKey={`sections-filter-semester:${filters.batch_id || ''}`}
            options={availableSemestersForFilters.map((item) => ({ value: item.id, label: item.label }))}
            loadOptions={(query) => loadSemesterOptions(query, filters.batch_id)}
            selectedLabel={semesterLabelById[filters.semester_id] || ''}
            allowEmpty
            disabled={!filters.batch_id}
            emptyLabel="All Semesters"
            placeholder={filters.batch_id ? 'Search semester' : 'Select batch first'}
            onValueChange={(value) =>
              updateFilters((prev) => ({
                ...prev,
                semester_id: value
              }))
            }
          />
        </div>
      </Card>

      {dashboard ? (
        <>
          <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-7">
            {[
              ['Sections', dashboard.total_sections || 0],
              ['Students', dashboard.total_students || 0],
              ['Offerings', dashboard.total_active_offerings || 0],
              ['Pending Evaluations', dashboard.total_pending_evaluations || 0],
              ['Unreleased Results', dashboard.total_unreleased_evaluations || 0],
              ['Timetable Drift', dashboard.sections_with_drift || 0],
              ['Unmapped Students', dashboard.global_unmapped_students || 0]
            ].map(([label, value]) => (
              <Card key={label} className="!p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </Card>
            ))}
          </div>
          <div className="grid gap-3 xl:grid-cols-[1.25fr_0.95fr]">
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Section Health</h2>
                <p className="text-sm text-slate-500">Operational summary across the currently filtered sections.</p>
              </div>
              <div className="hidden md:block">
                <Table columns={sectionHealthColumns} data={dashboard.sections || []} />
              </div>
              <div className="grid gap-3 md:hidden">
                {(dashboard.sections || []).map((row) => (
                  <div key={row.section_id} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-900">{row.section_name}</h3>
                        <p className="text-xs text-slate-500">
                          {row.student_count} students • {row.active_offering_count} offerings
                        </p>
                      </div>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-sm">
                        {row.latest_timetable_sync_status || row.latest_timetable_status || 'No timetable'}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                      <div className="rounded-xl bg-white px-3 py-2">
                        <p className="uppercase tracking-wide text-slate-400">Attendance</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">
                          {row.average_attendance_percent != null ? `${row.average_attendance_percent}%` : '-'}
                        </p>
                      </div>
                      <div className="rounded-xl bg-white px-3 py-2">
                        <p className="uppercase tracking-wide text-slate-400">Drift</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{row.latest_timetable_drift_count || 0}</p>
                      </div>
                      <div className="rounded-xl bg-white px-3 py-2">
                        <p className="uppercase tracking-wide text-slate-400">Unreleased</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{row.unreleased_evaluation_count || 0}</p>
                      </div>
                      <div className="rounded-xl bg-white px-3 py-2">
                        <p className="uppercase tracking-wide text-slate-400">Risk</p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{row.shortage_risk_count || 0} flagged</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Coordinator Priorities</h2>
                <p className="text-sm text-slate-500">
                  Focus sections with timetable drift, unreleased results, or attendance risk before editing hierarchy.
                </p>
              </div>
              <div className="space-y-3">
                {prioritySections.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                    No priority sections in the current filter.
                  </div>
                ) : (
                  prioritySections.map((row) => (
                    <div key={row.section_id} className="rounded-2xl border border-slate-200 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-medium text-slate-900">{row.section_name}</h3>
                          <p className="text-sm text-slate-500">
                            {row.student_count} students • {row.active_offering_count} offerings
                          </p>
                        </div>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                          Drift {row.latest_timetable_drift_count || 0}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs">
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">
                          Unreleased {row.unreleased_evaluation_count || 0}
                        </span>
                        <span className="rounded-full bg-rose-50 px-2.5 py-1 text-rose-700">
                          Attendance risk {row.shortage_risk_count || 0}
                        </span>
                        <span className="rounded-full bg-sky-50 px-2.5 py-1 text-sky-700">
                          Sync {row.latest_timetable_sync_status || row.latest_timetable_status || 'n/a'}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </>
      ) : null}

      {isAdmin ? (
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Create Section</h2>
          <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <SearchableSelect
              label="Faculty"
              value={form.faculty_id}
              loadKey="sections-form-faculty"
              options={faculties.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={loadFacultyOptions}
              selectedLabel={facultyNameById[form.faculty_id] || ''}
              placeholder="Search faculty"
              onValueChange={(value) => setForm((prev) => ({ ...prev, faculty_id: value, department_id: '', program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}
              required
            />
            <SearchableSelect
              label="Department"
              value={form.department_id}
              loadKey={`sections-form-department:${form.faculty_id || ''}`}
              options={availableDepartmentsForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadDepartmentOptions(query, form.faculty_id)}
              selectedLabel={departmentNameById[form.department_id] || ''}
              disabled={!form.faculty_id}
              placeholder={form.faculty_id ? 'Search department' : 'Select faculty first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, department_id: value, program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}
              required
            />
            <SearchableSelect
              label="Program"
              value={form.program_id}
              loadKey={`sections-form-program:${form.department_id || ''}`}
              options={availableProgramsForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadProgramOptions(query, form.department_id)}
              selectedLabel={programNameById[form.program_id] || ''}
              disabled={!form.department_id}
              placeholder={form.department_id ? 'Search program' : 'Select department first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, program_id: value, specialization_id: '', batch_id: '', semester_id: '' }))}
              required
            />
            <SearchableSelect
              label="Specialization"
              value={form.specialization_id}
              loadKey={`sections-form-specialization:${form.program_id || ''}`}
              options={availableSpecializationsForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadSpecializationOptions(query, form.program_id)}
              selectedLabel={specializationNameById[form.specialization_id] || ''}
              disabled={Boolean(selectedFormBatch) || !form.program_id}
              allowEmpty
              emptyLabel={
                selectedFormBatch
                  ? selectedFormBatch.specialization_id
                    ? 'Locked to batch specialization'
                    : 'Program-level batch'
                  : 'Select Specialization'
              }
              placeholder={form.program_id ? 'Search specialization' : 'Select program first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, specialization_id: value, batch_id: '', semester_id: '' }))}
            />
            <SearchableSelect
              label="Batch"
              value={form.batch_id}
              loadKey={`sections-form-batch:${form.program_id || ''}:${form.specialization_id || ''}`}
              options={availableBatchesForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadBatchOptions(query, form.program_id, form.specialization_id)}
              selectedLabel={batchNameById[form.batch_id] || ''}
              disabled={!form.program_id}
              placeholder={form.program_id ? 'Search batch' : 'Select program first'}
              onValueChange={handleFormBatchChange}
              required
            />
            <SearchableSelect
              label="Semester"
              value={form.semester_id}
              loadKey={`sections-form-semester:${form.batch_id || ''}`}
              options={availableSemestersForForm.map((item) => ({ value: item.id, label: item.label }))}
              loadOptions={(query) => loadSemesterOptions(query, form.batch_id)}
              selectedLabel={semesterLabelById[form.semester_id] || ''}
              disabled={!form.batch_id}
              placeholder={form.batch_id ? 'Search semester' : 'Select batch first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, semester_id: value }))}
              required
            />
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Section Name</span>
              <input className="input" required value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} placeholder="e.g. CSE 4A" />
            </label>
            <SearchableSelect
              label="Coordinator"
              value={form.class_coordinator_user_id}
              loadKey="sections-form-coordinator"
              options={teachers.map((teacher) => ({ value: teacher.id, label: teacher.full_name }))}
              loadOptions={loadTeacherOptions}
              selectedLabel={teacherNameById[form.class_coordinator_user_id] || ''}
              disabled={!isAdmin}
              allowEmpty
              emptyLabel="No Coordinator"
              placeholder={isAdmin ? 'Search teacher' : 'Unavailable'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, class_coordinator_user_id: value }))}
            />
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full">Create</button>
            </div>
          </form>
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Sections List</h2>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>Prev</button>
            <span className="text-xs text-slate-500">Page {Math.floor(skip / limit) + 1}</span>
            <button className="btn-secondary" disabled={rows.length < limit} onClick={() => setSkip(skip + limit)}>Next</button>
            <select className="input w-24" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>
        </div>
        {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <Table columns={columns} data={rows} />
      </Card>
    </div>
  );
}
