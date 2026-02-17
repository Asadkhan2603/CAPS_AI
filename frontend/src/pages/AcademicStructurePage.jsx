import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

export default function AcademicStructurePage() {
  const { pushToast } = useToast();
  const [payload, setPayload] = useState({ university: null, courses: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [courseId, setCourseId] = useState('');
  const [yearId, setYearId] = useState('');
  const [classId, setClassId] = useState('');

  async function loadStructure() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/analytics/academic-structure');
      const next = response.data || { university: null, courses: [] };
      setPayload(next);
      const firstCourse = next.courses?.[0];
      const firstYear = firstCourse?.years?.[0];
      const firstClass = firstYear?.classes?.[0];
      setCourseId(firstCourse?.id || '');
      setYearId(firstYear?.id || '');
      setClassId(firstClass?.id || '');
    } catch (err) {
      const message = formatApiError(err, 'Failed to load academic hierarchy');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setPayload({ university: null, courses: [] });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStructure();
  }, []);

  const courses = payload.courses || [];
  const selectedCourse = courses.find((item) => item.id === courseId) || null;
  const years = selectedCourse?.years || [];
  const selectedYear = years.find((item) => item.id === yearId) || null;
  const classes = selectedYear?.classes || [];
  const selectedClass = classes.find((item) => item.id === classId) || null;

  const studentColumns = useMemo(
    () => [
      { key: 'id', label: 'Student ID' },
      { key: 'name', label: 'Name' },
      { key: 'rollNo', label: 'Roll No.' },
      { key: 'assignment_submissions', label: 'Submission Logs', render: (row) => row.logs?.assignment_submissions ?? 0 },
      { key: 'event_registrations', label: 'Event Registration Logs', render: (row) => row.logs?.event_registrations ?? 0 }
    ],
    []
  );

  const subjectColumns = useMemo(
    () => [
      { key: 'id', label: 'Subject ID' },
      { key: 'name', label: 'Name' },
      { key: 'code', label: 'Code' }
    ],
    []
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Academic Structure</h1>
          <button className="btn-secondary" onClick={loadStructure}>Refresh</button>
        </div>
        {payload.university ? (
          <p className="text-sm text-slate-500">
            {payload.university.name} ({payload.university.id}) - {payload.university.location}
          </p>
        ) : null}
        {loading ? <p className="text-sm text-slate-500">Loading hierarchy...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Course -&gt; Year -&gt; Class</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Course</span>
            <select
              className="input"
              value={courseId}
              onChange={(e) => {
                const nextCourseId = e.target.value;
                const nextCourse = courses.find((item) => item.id === nextCourseId) || null;
                const nextYear = nextCourse?.years?.[0] || null;
                const nextClass = nextYear?.classes?.[0] || null;
                setCourseId(nextCourseId);
                setYearId(nextYear?.id || '');
                setClassId(nextClass?.id || '');
              }}
            >
              <option value="">Select Course</option>
              {courses.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Year</span>
            <select
              className="input"
              value={yearId}
              onChange={(e) => {
                const nextYearId = e.target.value;
                const nextYear = years.find((item) => item.id === nextYearId) || null;
                const nextClass = nextYear?.classes?.[0] || null;
                setYearId(nextYearId);
                setClassId(nextClass?.id || '');
              }}
            >
              <option value="">Select Year</option>
              {years.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Class</span>
            <select className="input" value={classId} onChange={(e) => setClassId(e.target.value)}>
              <option value="">Select Class</option>
              {classes.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Classes</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {classes.map((item) => (
            <button
              key={item.id}
              className={`rounded-2xl border p-4 text-left transition ${classId === item.id ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-slate-200 dark:border-slate-800'}`}
              onClick={() => setClassId(item.id)}
            >
              <p className="text-base font-semibold">{item.name}</p>
              <p className="text-xs text-slate-500">Coordinator: {item.coordinator || 'Unassigned'}</p>
              <p className="mt-2 text-sm">Students: {item.students?.length || 0}</p>
              <p className="text-sm">Subjects: {item.subjects?.length || 0}</p>
            </button>
          ))}
          {!classes.length ? <p className="text-sm text-slate-500">No classes found for selected path.</p> : null}
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Students List + Logs</h2>
        <Table columns={studentColumns} data={selectedClass?.students || []} />
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Subjects</h2>
        <Table columns={subjectColumns} data={selectedClass?.subjects || []} />
      </Card>
    </div>
  );
}
