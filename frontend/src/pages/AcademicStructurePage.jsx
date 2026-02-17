import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

export default function AcademicStructurePage() {
  const { pushToast } = useToast();
  const [payload, setPayload] = useState({ university: null, faculties: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [facultyId, setFacultyId] = useState('');
  const [courseId, setCourseId] = useState('');
  const [yearId, setYearId] = useState('');
  const [branchId, setBranchId] = useState('');
  const [sectionId, setSectionId] = useState('');

  async function loadStructure() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/analytics/academic-structure');
      const next = response.data || { university: null, faculties: [] };
      setPayload(next);
      const firstFaculty = next.faculties?.[0];
      const firstCourse = firstFaculty?.courses?.[0];
      const firstYear = firstCourse?.years?.[0];
      const firstBranch = firstYear?.branches?.[0];
      const firstSection = firstBranch?.sections?.[0];
      setFacultyId(firstFaculty?.id || '');
      setCourseId(firstCourse?.id || '');
      setYearId(firstYear?.id || '');
      setBranchId(firstBranch?.id || '');
      setSectionId(firstSection?.id || '');
    } catch (err) {
      const message = formatApiError(err, 'Failed to load academic hierarchy');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setPayload({ university: null, faculties: [] });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStructure();
  }, []);

  const faculties = payload.faculties || [];
  const selectedFaculty = faculties.find((item) => item.id === facultyId) || null;
  const courses = selectedFaculty?.courses || [];
  const selectedCourse = courses.find((item) => item.id === courseId) || null;
  const years = selectedCourse?.years || [];
  const selectedYear = years.find((item) => item.id === yearId) || null;
  const branches = selectedYear?.branches || [];
  const selectedBranch = branches.find((item) => item.id === branchId) || null;
  const sections = selectedBranch?.sections || [];
  const selectedSection = sections.find((item) => item.id === sectionId) || null;

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
        <h2 className="text-lg font-semibold">Faculty -&gt; Course -&gt; Year -&gt; Branch -&gt; Section</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Faculty</span>
            <select
              className="input"
              value={facultyId}
              onChange={(e) => {
                const nextFacultyId = e.target.value;
                const nextFaculty = faculties.find((item) => item.id === nextFacultyId) || null;
                const nextCourse = nextFaculty?.courses?.[0] || null;
                const nextYear = nextCourse?.years?.[0] || null;
                const nextBranch = nextYear?.branches?.[0] || null;
                const nextSection = nextBranch?.sections?.[0] || null;
                setFacultyId(nextFacultyId);
                setCourseId(nextCourse?.id || '');
                setYearId(nextYear?.id || '');
                setBranchId(nextBranch?.id || '');
                setSectionId(nextSection?.id || '');
              }}
            >
              <option value="">Select Faculty</option>
              {faculties.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Course</span>
            <select
              className="input"
              value={courseId}
              onChange={(e) => {
                const nextCourseId = e.target.value;
                const nextCourse = courses.find((item) => item.id === nextCourseId) || null;
                const nextYear = nextCourse?.years?.[0] || null;
                const nextBranch = nextYear?.branches?.[0] || null;
                const nextSection = nextBranch?.sections?.[0] || null;
                setCourseId(nextCourseId);
                setYearId(nextYear?.id || '');
                setBranchId(nextBranch?.id || '');
                setSectionId(nextSection?.id || '');
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
                const nextBranch = nextYear?.branches?.[0] || null;
                const nextSection = nextBranch?.sections?.[0] || null;
                setYearId(nextYearId);
                setBranchId(nextBranch?.id || '');
                setSectionId(nextSection?.id || '');
              }}
            >
              <option value="">Select Year</option>
              {years.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Branch</span>
            <select
              className="input"
              value={branchId}
              onChange={(e) => {
                const nextBranchId = e.target.value;
                const nextBranch = branches.find((item) => item.id === nextBranchId) || null;
                const nextSection = nextBranch?.sections?.[0] || null;
                setBranchId(nextBranchId);
                setSectionId(nextSection?.id || '');
              }}
            >
              <option value="">Select Branch</option>
              {branches.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Section</span>
            <select className="input" value={sectionId} onChange={(e) => setSectionId(e.target.value)}>
              <option value="">Select Section</option>
              {sections.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Section Tiles</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {sections.map((section) => (
            <button
              key={section.id}
              className={`rounded-2xl border p-4 text-left transition ${sectionId === section.id ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-slate-200 dark:border-slate-800'}`}
              onClick={() => setSectionId(section.id)}
            >
              <p className="text-base font-semibold">{section.name}</p>
              <p className="text-xs text-slate-500">Teacher: {section.teacher || 'Unassigned'}</p>
              <p className="mt-2 text-sm">Students: {section.students?.length || 0}</p>
            </button>
          ))}
          {!sections.length ? <p className="text-sm text-slate-500">No sections found for selected path.</p> : null}
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Students List + Logs</h2>
        <Table columns={studentColumns} data={selectedSection?.students || []} />
      </Card>
    </div>
  );
}
