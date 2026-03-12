import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { createSection, getSections } from '../services/sectionsApi';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';

export default function ClassesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const { pushToast } = useToast();

  const [rows, setRows] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [teachers, setTeachers] = useState([]);

  const [loading, setLoading] = useState(false);
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

  const facultyNameById = useMemo(() => Object.fromEntries(faculties.map((item) => [item.id, item.name])), [faculties]);
  const departmentNameById = useMemo(() => Object.fromEntries(departments.map((item) => [item.id, item.name])), [departments]);
  const programNameById = useMemo(() => Object.fromEntries(programs.map((item) => [item.id, item.name])), [programs]);
  const specializationNameById = useMemo(
    () => Object.fromEntries(specializations.map((item) => [item.id, item.name])),
    [specializations]
  );
  const batchNameById = useMemo(() => Object.fromEntries(batches.map((item) => [item.id, item.name])), [batches]);
  const semesterLabelById = useMemo(() => Object.fromEntries(semesters.map((item) => [item.id, item.label])), [semesters]);
  const teacherNameById = useMemo(() => Object.fromEntries(teachers.map((item) => [item.id, item.full_name])), [teachers]);

  const availableDepartmentsForForm = useMemo(
    () => departments.filter((item) => !form.faculty_id || item.faculty_id === form.faculty_id),
    [departments, form.faculty_id]
  );
  const availableProgramsForForm = useMemo(
    () => programs.filter((item) => !form.department_id || item.department_id === form.department_id),
    [programs, form.department_id]
  );
  const availableSpecializationsForForm = useMemo(
    () => specializations.filter((item) => !form.program_id || item.program_id === form.program_id),
    [specializations, form.program_id]
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
    () => specializations.filter((item) => !filters.program_id || item.program_id === filters.program_id),
    [specializations, filters.program_id]
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

  async function loadLookups() {
    const requests = [
      apiClient.get('/faculties/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/departments/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/programs/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/specializations/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/batches/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/semesters/', { params: { skip: 0, limit: 100 } })
    ];
    if (isAdmin) requests.push(apiClient.get('/users/'));
    const results = await Promise.allSettled(requests);

    setFaculties(results[0].status === 'fulfilled' ? results[0].value.data || [] : []);
    setDepartments(results[1].status === 'fulfilled' ? results[1].value.data || [] : []);
    setPrograms(results[2].status === 'fulfilled' ? results[2].value.data || [] : []);
    setSpecializations(results[3].status === 'fulfilled' ? results[3].value.data || [] : []);
    setBatches(results[4].status === 'fulfilled' ? results[4].value.data || [] : []);
    setSemesters(results[5].status === 'fulfilled' ? results[5].value.data || [] : []);
    setTeachers(
      isAdmin && results[6]?.status === 'fulfilled'
        ? (results[6].value.data || []).filter((item) => item.role === 'teacher')
        : []
    );
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

  useEffect(() => {
    loadLookups();
  }, []);

  useEffect(() => {
    loadSections();
  }, [skip, limit, filters]);

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

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Section' },
      { key: 'faculty_id', label: 'Faculty', render: (row) => facultyNameById[row.faculty_id] || '-' },
      { key: 'department_id', label: 'Department', render: (row) => departmentNameById[row.department_id] || '-' },
      { key: 'program_id', label: 'Program', render: (row) => programNameById[row.program_id] || '-' },
      {
        key: 'specialization_id',
        label: 'Specialization',
        render: (row) => specializationNameById[row.specialization_id] || '-'
      },
      { key: 'batch_id', label: 'Batch', render: (row) => batchNameById[row.batch_id] || '-' },
      { key: 'semester_id', label: 'Semester', render: (row) => semesterLabelById[row.semester_id] || '-' },
      {
        key: 'class_coordinator_user_id',
        label: 'Coordinator',
        render: (row) =>
          row.class_coordinator_user_id
            ? teacherNameById[row.class_coordinator_user_id] || row.class_coordinator_user_id
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

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Sections</h1>
          <button className="btn-secondary" onClick={() => { setSkip(0); loadSections(); }}>Refresh</button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Faculty</span>
            <select className="input" value={filters.faculty_id} onChange={(e) => setFilters((prev) => ({ ...prev, faculty_id: e.target.value, department_id: '', program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}>
              <option value="">All Faculties</option>
              {faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Department</span>
            <select className="input" value={filters.department_id} onChange={(e) => setFilters((prev) => ({ ...prev, department_id: e.target.value, program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}>
              <option value="">All Departments</option>
              {availableDepartmentsForFilters.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Program</span>
            <select className="input" value={filters.program_id} onChange={(e) => setFilters((prev) => ({ ...prev, program_id: e.target.value, specialization_id: '', batch_id: '', semester_id: '' }))}>
              <option value="">All Programs</option>
              {availableProgramsForFilters.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Specialization</span>
            <select className="input" value={filters.specialization_id} onChange={(e) => setFilters((prev) => ({ ...prev, specialization_id: e.target.value, batch_id: '', semester_id: '' }))}>
              <option value="">All Specializations</option>
              {availableSpecializationsForFilters.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Batch</span>
            <select className="input" value={filters.batch_id} onChange={(e) => setFilters((prev) => ({ ...prev, batch_id: e.target.value, semester_id: '' }))}>
              <option value="">All Batches</option>
              {availableBatchesForFilters.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Semester</span>
            <select className="input" value={filters.semester_id} onChange={(e) => setFilters((prev) => ({ ...prev, semester_id: e.target.value }))}>
              <option value="">All Semesters</option>
              {availableSemestersForFilters.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label>
        </div>
      </Card>

      {isAdmin ? (
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Create Section</h2>
          <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Faculty</span>
              <select className="input" value={form.faculty_id} onChange={(e) => setForm((prev) => ({ ...prev, faculty_id: e.target.value, department_id: '', program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}>
                <option value="">Select Faculty</option>
                {faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Department</span>
              <select className="input" value={form.department_id} onChange={(e) => setForm((prev) => ({ ...prev, department_id: e.target.value, program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}>
                <option value="">Select Department</option>
                {availableDepartmentsForForm.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Program</span>
              <select className="input" value={form.program_id} onChange={(e) => setForm((prev) => ({ ...prev, program_id: e.target.value, specialization_id: '', batch_id: '', semester_id: '' }))}>
                <option value="">Select Program</option>
                {availableProgramsForForm.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Specialization</span>
              <select className="input" value={form.specialization_id} onChange={(e) => setForm((prev) => ({ ...prev, specialization_id: e.target.value, batch_id: '', semester_id: '' }))}>
                <option value="">Select Specialization</option>
                {availableSpecializationsForForm.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Batch</span>
              <select className="input" value={form.batch_id} onChange={(e) => setForm((prev) => ({ ...prev, batch_id: e.target.value, semester_id: '' }))}>
                <option value="">Select Batch</option>
                {availableBatchesForForm.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Semester</span>
              <select className="input" value={form.semester_id} onChange={(e) => setForm((prev) => ({ ...prev, semester_id: e.target.value }))}>
                <option value="">Select Semester</option>
                {availableSemestersForForm.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Section Name</span>
              <input className="input" required value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} placeholder="e.g. CSE 4A" />
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Coordinator</span>
              <select className="input" value={form.class_coordinator_user_id} onChange={(e) => setForm((prev) => ({ ...prev, class_coordinator_user_id: e.target.value }))}>
                <option value="">No Coordinator</option>
                {teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.full_name} ({teacher.email})</option>)}
              </select>
            </label>
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
            <span className="text-xs text-slate-500">skip: {skip}</span>
            <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>Next</button>
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
