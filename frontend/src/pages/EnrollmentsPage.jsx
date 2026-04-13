import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { getSectionDashboard, getSections } from '../services/sectionsApi';
import { useAuth } from '../hooks/useAuth';

function canManageEnrollments(user) {
  if (!user) return false;
  if (user.role === 'admin') return true;
  if (user.role !== 'teacher') return false;
  const extensions = user.extended_roles || [];
  return extensions.includes('year_head') || extensions.includes('class_coordinator');
}

export default function EnrollmentsPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    async function loadLookups() {
      try {
        const sectionsReq = getSections({ skip: 0, limit: 100 });
        const [sectionsRes, studentsRes, dashboardRes] = await Promise.all([
          sectionsReq,
          apiClient.get('/students/', { params: { skip: 0, limit: 100 } }),
          getSectionDashboard()
        ]);
        setSections(sectionsRes.data || []);
        setStudents(studentsRes.data || []);
        setDashboard(dashboardRes || null);
      } catch {
        setSections([]);
        setStudents([]);
        setDashboard(null);
      }
    }
    loadLookups();
  }, []);

  const sectionOptions = useMemo(
    () => sections.map((item) => ({ value: item.id, label: item.name })),
    [sections]
  );
  const studentOptions = useMemo(
    () => students.map((item) => ({ value: item.roll_number, label: `${item.full_name} (${item.roll_number})` })),
    [students]
  );
  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );
  const studentNameById = useMemo(() => {
    const map = {};
    for (const item of students) {
      const label = `${item.full_name} (${item.roll_number})`;
      if (item.id) map[item.id] = label;
      if (item.roll_number) map[item.roll_number] = label;
    }
    return map;
  }, [students]);
  const filters = useMemo(
    () => [
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'student_id', label: 'Enrollment Number', type: 'select', options: studentOptions, placeholder: 'All Students' }
    ],
    [sectionOptions, studentOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, required: true },
      { name: 'student_id', label: 'Enrollment Number', type: 'select', options: studentOptions, required: true }
    ],
    [sectionOptions, studentOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'class_id', label: 'Section', render: (row) => sectionNameById[row.class_id] || row.class_id },
      {
        key: 'student_id',
        label: 'Student',
        render: (row) =>
          studentNameById[row.student_id] ||
          studentNameById[row.student_roll_number] ||
          row.student_roll_number ||
          row.student_id
      },
      { key: 'assigned_by_user_id', label: 'Assigned By' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [sectionNameById, studentNameById]
  );

  const enrollmentSummary = useMemo(() => {
    const canonical = students.filter((item) => item.placement_source === 'enrollment').length;
    const legacyOnly = students.filter((item) => item.class_id && item.placement_source !== 'enrollment').length;
    return {
      canonical,
      legacyOnly,
      totalStudents: students.length,
      sections: dashboard?.total_sections || 0,
      unmapped:
        students.filter((item) => {
          const source = item.placement_source || '';
          return !item.class_id && source !== 'enrollment';
        }).length || 0
    };
  }, [dashboard?.total_sections, students]);

  const cleanupIntent = searchParams.get('cleanup') || '';
  const cleanupSource = searchParams.get('source') || '';
  const committedFromBulk = Number(searchParams.get('committed') || 0);

  const cleanupStudents = useMemo(() => {
    if (cleanupIntent === 'legacy-only') {
      return students.filter((item) => item.class_id && item.placement_source !== 'enrollment');
    }
    if (cleanupIntent === 'unmapped') {
      return students.filter((item) => {
        const source = item.placement_source || '';
        return !item.class_id && source !== 'enrollment';
      });
    }
    return [];
  }, [cleanupIntent, students]);

  const cleanupTitle =
    cleanupIntent === 'legacy-only'
      ? 'Legacy profile-only cleanup'
      : cleanupIntent === 'unmapped'
        ? 'Unmapped student cleanup'
        : '';

  const cleanupDescription =
    cleanupIntent === 'legacy-only'
      ? 'These students still depend on legacy profile section fields instead of canonical enrollments.'
      : cleanupIntent === 'unmapped'
        ? 'These students do not yet have canonical section placement through enrollments.'
        : '';

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <h1 className="text-2xl font-semibold">Enrollments</h1>
        <p className="text-sm text-slate-500">Enrollments are the canonical source of section placement. Use this workflow to place students, not just profile `Section` edits.</p>
      </Card>
      {cleanupIntent ? (
        <Card className="space-y-3 border-sky-200 bg-sky-50/70">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">Cleanup Focus</p>
              <h2 className="mt-1 text-lg font-semibold text-sky-950">{cleanupTitle}</h2>
              <p className="mt-1 text-sm text-sky-900/80">
                {cleanupDescription}
                {cleanupSource === 'bulk-create' && committedFromBulk > 0
                  ? ` The latest bulk create committed ${committedFromBulk} rows, so review these students before leaving the workflow.`
                  : ''}
              </p>
            </div>
            <button
              type="button"
              className="btn-secondary !border-sky-300 !bg-white !text-sky-800 hover:!bg-sky-100"
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.delete('cleanup');
                next.delete('source');
                next.delete('committed');
                setSearchParams(next, { replace: true });
              }}
            >
              Clear Focus
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-sky-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Students In Focus</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">{cleanupStudents.length}</p>
            </div>
            <div className="rounded-2xl border border-sky-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Committed In Last Bulk Run</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">{committedFromBulk || 0}</p>
            </div>
            <div className="rounded-2xl border border-sky-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Recommended Action</p>
              <p className="mt-1 text-sm font-medium text-slate-900">Create enrollments for these students before editing other academic flows.</p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-900">Students needing cleanup</h3>
              <span className="text-xs text-slate-500">Showing first 12</span>
            </div>
            {cleanupStudents.length ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {cleanupStudents.slice(0, 12).map((item) => (
                  <div key={item.id || item.roll_number} className="rounded-2xl border border-sky-200 bg-white px-4 py-3">
                    <h4 className="text-sm font-semibold text-slate-900">{item.full_name || 'Student'}</h4>
                    <p className="mt-1 text-xs text-slate-500">
                      Roll {item.roll_number || '-'}{item.enrollment_number ? ` • Enrollment ${item.enrollment_number}` : ''}
                    </p>
                    <p className="mt-2 text-xs text-slate-600">
                      Placement source: {item.placement_source || 'profile-only'}
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      Current section: {item.class_id ? sectionNameById[item.class_id] || item.class_id : 'None'}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
                No students currently match this cleanup focus.
              </div>
            )}
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Link className="btn-secondary" to="/students/bulk-import">
                Back to Bulk Create Students
              </Link>
            </div>
          </div>
        </Card>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ['Students Loaded', enrollmentSummary.totalStudents],
          ['Enrollment-backed', enrollmentSummary.canonical],
          ['Legacy Profile Only', enrollmentSummary.legacyOnly],
          ['Unmapped Students', enrollmentSummary.unmapped],
          ['Sections In Scope', enrollmentSummary.sections]
        ].map(([label, value]) => (
          <Card key={label} className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold">{value}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold">Enrollment Checklist</h2>
            <p className="text-sm text-slate-500">
              Use this order on tablet and mobile to avoid cross-section placement mistakes.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ['1. Find student', 'Search by roll number first so you update the correct academic profile.'],
              ['2. Confirm target section', 'Check the section before submit because enrollments define the canonical placement.'],
              ['3. Review gaps', 'Return here after mapping to make sure unmapped and legacy-only counts drop.']
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
            <h2 className="text-lg font-semibold">Placement Risk Snapshot</h2>
            <p className="text-sm text-slate-500">Quick health view for coordinators before bulk mapping or cleanup.</p>
          </div>
          <div className="space-y-3">
            {[
              ['Enrollment-backed students', `${enrollmentSummary.canonical} already follow canonical placement.`],
              ['Legacy profile-only students', `${enrollmentSummary.legacyOnly} still rely on profile section fields.`],
              ['Unmapped students', `${enrollmentSummary.unmapped} still need section placement.`]
            ].map(([title, body]) => (
              <div key={title} className="rounded-2xl border border-slate-200 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
                <p className="mt-1 text-sm text-slate-600">{body}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <EntityManager
        title="Enrollment Workspace"
        endpoint="/enrollments/"
        filters={filters}
        createFields={createFields}
        columns={columns}
        hideCreate={!canManageEnrollments(user)}
      />
    </div>
  );
}
