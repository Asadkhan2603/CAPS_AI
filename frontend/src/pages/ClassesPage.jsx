import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

export default function ClassesPage() {
  const { pushToast } = useToast();
  const [rows, setRows] = useState([]);
  const [courses, setCourses] = useState([]);
  const [years, setYears] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [filters, setFilters] = useState({ course_id: '', year_id: '', department_code: '', branch_code: '' });
  const [form, setForm] = useState({
    course_id: '',
    year_id: '',
    name: '',
    department_code: '',
    branch_code: '',
    class_coordinator_user_id: ''
  });

  const courseNameById = useMemo(
    () => Object.fromEntries(courses.map((item) => [item.id, item.name])),
    [courses]
  );
  const yearLabelById = useMemo(
    () => Object.fromEntries(years.map((item) => [item.id, item.label || `Year ${item.year_number}`])),
    [years]
  );
  const teacherNameById = useMemo(
    () => Object.fromEntries(teachers.map((item) => [item.id, item.full_name])),
    [teachers]
  );
  const departmentNameByCode = useMemo(
    () => Object.fromEntries(departments.map((item) => [item.code, item.name])),
    [departments]
  );
  const branchNameByCode = useMemo(
    () => Object.fromEntries(branches.map((item) => [item.code, item.name])),
    [branches]
  );

  const availableYearsForForm = useMemo(
    () => years.filter((item) => !form.course_id || item.course_id === form.course_id),
    [years, form.course_id]
  );
  const availableBranchesForForm = useMemo(
    () => branches.filter((item) => !form.department_code || item.department_code === form.department_code),
    [branches, form.department_code]
  );
  const availableBranchesForFilters = useMemo(
    () => branches.filter((item) => !filters.department_code || item.department_code === filters.department_code),
    [branches, filters.department_code]
  );

  async function loadLookups() {
    const [coursesRes, yearsRes, usersRes, departmentsRes, branchesRes] = await Promise.allSettled([
      apiClient.get('/courses/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/years/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/users/'),
      apiClient.get('/departments/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/branches/', { params: { skip: 0, limit: 200 } })
    ]);

    setCourses(coursesRes.status === 'fulfilled' ? (coursesRes.value.data || []) : []);
    setYears(yearsRes.status === 'fulfilled' ? (yearsRes.value.data || []) : []);
    setTeachers(
      usersRes.status === 'fulfilled'
        ? ((usersRes.value.data || []).filter((user) => user.role === 'teacher'))
        : []
    );
    setDepartments(departmentsRes.status === 'fulfilled' ? (departmentsRes.value.data || []) : []);
    setBranches(branchesRes.status === 'fulfilled' ? (branchesRes.value.data || []) : []);

    if (
      coursesRes.status === 'rejected' ||
      yearsRes.status === 'rejected' ||
      usersRes.status === 'rejected' ||
      departmentsRes.status === 'rejected' ||
      branchesRes.status === 'rejected'
    ) {
      pushToast({
        title: 'Partial load warning',
        description: 'Some reference data failed to load. Try Refresh.',
        variant: 'error'
      });
    }
  }

  async function loadClasses() {
    setLoading(true);
    setError('');
    try {
      const selectedDepartmentName = departmentNameByCode[filters.department_code];
      const selectedBranchName = branchNameByCode[filters.branch_code];
      const response = await apiClient.get('/classes/', {
        params: {
          course_id: filters.course_id || undefined,
          year_id: filters.year_id || undefined,
          faculty_name: selectedDepartmentName || undefined,
          branch_name: selectedBranchName || undefined,
          skip,
          limit
        }
      });
      setRows(response.data || []);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load classes');
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
    loadClasses();
  }, [skip, limit, filters.department_code, filters.branch_code, departmentNameByCode, branchNameByCode]);

  async function onCreate(event) {
    event.preventDefault();
    setError('');
    try {
      await apiClient.post('/classes/', {
        course_id: form.course_id,
        year_id: form.year_id,
        name: form.name,
        faculty_name: form.department_code ? (departmentNameByCode[form.department_code] || null) : null,
        branch_name: form.branch_code ? (branchNameByCode[form.branch_code] || null) : null,
        class_coordinator_user_id: form.class_coordinator_user_id || null
      });
      pushToast({ title: 'Created', description: 'Class created successfully.', variant: 'success' });
      setForm({
        course_id: '',
        year_id: '',
        name: '',
        department_code: '',
        branch_code: '',
        class_coordinator_user_id: ''
      });
      setSkip(0);
      await loadClasses();
    } catch (err) {
      const message = formatApiError(err, 'Failed to create class');
      setError(message);
      pushToast({ title: 'Create failed', description: message, variant: 'error' });
    }
  }

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Name' },
      { key: 'faculty_name', label: 'Department', render: (row) => row.faculty_name || '-' },
      { key: 'branch_name', label: 'Branch', render: (row) => row.branch_name || '-' },
      { key: 'course_id', label: 'Course', render: (row) => courseNameById[row.course_id] || row.course_id },
      { key: 'year_id', label: 'Year', render: (row) => yearLabelById[row.year_id] || row.year_id },
      {
        key: 'class_coordinator_user_id',
        label: 'Coordinator',
        render: (row) =>
          row.class_coordinator_user_id
            ? teacherNameById[row.class_coordinator_user_id] || row.class_coordinator_user_id
            : '-'
      }
    ],
    [courseNameById, yearLabelById, teacherNameById]
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Classes</h1>
          <button className="btn-secondary" onClick={() => { setSkip(0); loadClasses(); }}>Refresh</button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Course</span>
            <select
              className="input"
              value={filters.course_id}
              onChange={(e) => setFilters((prev) => ({ ...prev, course_id: e.target.value }))}
            >
              <option value="">All Courses</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>{course.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Year</span>
            <select
              className="input"
              value={filters.year_id}
              onChange={(e) => setFilters((prev) => ({ ...prev, year_id: e.target.value }))}
            >
              <option value="">All Years</option>
              {years.map((year) => (
                <option key={year.id} value={year.id}>{year.label || `Year ${year.year_number}`}</option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Department</span>
            <select
              className="input"
              value={filters.department_code}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, department_code: e.target.value, branch_code: '' }))
              }
            >
              <option value="">All Departments</option>
              {departments.map((department) => (
                <option key={department.id} value={department.code}>{department.name}</option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Branch</span>
            <select
              className="input"
              value={filters.branch_code}
              onChange={(e) => setFilters((prev) => ({ ...prev, branch_code: e.target.value }))}
            >
              <option value="">All Branches</option>
              {availableBranchesForFilters.map((branch) => (
                <option key={branch.id} value={branch.code}>{branch.name}</option>
              ))}
            </select>
          </label>

          <div className="flex items-end">
            <button
              className="btn-secondary"
              onClick={() => {
                setSkip(0);
                loadClasses();
              }}
            >
              Apply Filters
            </button>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold">Create Class</h2>
        <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Course</span>
            <select
              className="input"
              value={form.course_id}
              required
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  course_id: e.target.value,
                  year_id: ''
                }))
              }
            >
              <option value="">Select Course</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>{course.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Year</span>
            <select
              className="input"
              value={form.year_id}
              required
              onChange={(e) => setForm((prev) => ({ ...prev, year_id: e.target.value }))}
            >
              <option value="">Select Year</option>
              {availableYearsForForm.map((year) => (
                <option key={year.id} value={year.id}>{year.label || `Year ${year.year_number}`}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Class Name</span>
            <input
              className="input"
              required
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. B.Tech CSE 2nd Year A"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Department</span>
            <select
              className="input"
              value={form.department_code}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, department_code: e.target.value, branch_code: '' }))
              }
            >
              <option value="">Select Department</option>
              {departments.map((department) => (
                <option key={department.id} value={department.code}>{department.name}</option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Branch</span>
            <select
              className="input"
              value={form.branch_code}
              onChange={(e) => setForm((prev) => ({ ...prev, branch_code: e.target.value }))}
            >
              <option value="">Select Branch</option>
              {availableBranchesForForm.map((branch) => (
                <option key={branch.id} value={branch.code}>{branch.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Coordinator (Teacher)</span>
            <select
              className="input"
              value={form.class_coordinator_user_id}
              onChange={(e) => setForm((prev) => ({ ...prev, class_coordinator_user_id: e.target.value }))}
            >
              <option value="">No Coordinator</option>
              {teachers.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>{teacher.full_name} ({teacher.email})</option>
              ))}
            </select>
          </label>

          <div className="flex items-end">
            <button type="submit" className="btn-primary w-full">Create</button>
          </div>
        </form>
      </Card>

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Classes List</h2>
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
