import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, CheckCircle2, Search } from 'lucide-react';
import EntityManager from '../components/ui/EntityManager';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

export default function EvaluationsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [studentRows, setStudentRows] = useState([]);
  const [studentLoading, setStudentLoading] = useState(false);
  const [studentFilter, setStudentFilter] = useState({ finalized: '', query: '' });

  useEffect(() => {
    async function loadLookups() {
      if (isStudent) {
        try {
          const [submissionsRes, evaluationsRes] = await Promise.all([
            apiClient.get('/submissions/', { params: { skip: 0, limit: 200 } }),
            apiClient.get('/evaluations/', { params: { skip: 0, limit: 200 } })
          ]);
          setSubmissions(submissionsRes.data || []);
          setStudentRows(evaluationsRes.data || []);
        } catch {
          setSubmissions([]);
          setStudentRows([]);
        } finally {
          setStudentLoading(false);
        }
        return;
      }

      try {
        const [submissionsRes, usersRes] = await Promise.all([
          apiClient.get('/submissions/', { params: { skip: 0, limit: 100 } }),
          apiClient.get('/users/')
        ]);
        setSubmissions(submissionsRes.data || []);
        setUsers(usersRes.data || []);
      } catch {
        setSubmissions([]);
        setUsers([]);
      }
    }
    if (isStudent) {
      setStudentLoading(true);
    }
    loadLookups();
  }, [isStudent]);

  const submissionOptions = useMemo(
    () =>
      submissions.map((item) => ({
        value: item.id,
        label: `${item.original_filename || 'Submission'} (${item.id})`
      })),
    [submissions]
  );
  const studentOptions = useMemo(
    () =>
      users
        .filter((item) => item.role === 'student')
        .map((item) => ({ value: item.id, label: `${item.full_name} (${item.email})` })),
    [users]
  );
  const teacherOptions = useMemo(
    () =>
      users
        .filter((item) => item.role === 'teacher')
        .map((item) => ({ value: item.id, label: `${item.full_name} (${item.email})` })),
    [users]
  );
  const submissionLabelById = useMemo(
    () => Object.fromEntries(submissionOptions.map((item) => [item.value, item.label])),
    [submissionOptions]
  );
  const studentLabelById = useMemo(
    () => Object.fromEntries(studentOptions.map((item) => [item.value, item.label])),
    [studentOptions]
  );
  const teacherLabelById = useMemo(
    () => Object.fromEntries(teacherOptions.map((item) => [item.value, item.label])),
    [teacherOptions]
  );

  const filters = useMemo(
    () => [
      { name: 'submission_id', label: 'Submission', type: 'select', options: submissionOptions, placeholder: 'All Submissions' },
      { name: 'student_user_id', label: 'Student', type: 'select', options: studentOptions, placeholder: 'All Students' },
      { name: 'teacher_user_id', label: 'Teacher', type: 'select', options: teacherOptions, placeholder: 'All Teachers' },
      { name: 'is_finalized', label: 'Finalized', type: 'switch' }
    ],
    [studentOptions, submissionOptions, teacherOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'submission_id', label: 'Submission', type: 'select', options: submissionOptions, required: true },
      { name: 'attendance_percent', label: 'Attendance %', type: 'number', min: 0, max: 100, required: true, defaultValue: 85 },
      { name: 'skill', label: 'Skill (0-2.5)', type: 'number', min: 0, max: 2.5, required: true, defaultValue: 2 },
      { name: 'behavior', label: 'Behavior (0-2.5)', type: 'number', min: 0, max: 2.5, required: true, defaultValue: 2 },
      { name: 'report', label: 'Report (0-10)', type: 'number', min: 0, max: 10, required: true, defaultValue: 8 },
      { name: 'viva', label: 'Viva (0-20)', type: 'number', min: 0, max: 20, required: true, defaultValue: 15 },
      { name: 'final_exam', label: 'Final Exam (0-60)', type: 'number', min: 0, max: 60, required: true, defaultValue: 40 },
      { name: 'remarks', label: 'Remarks', nullable: true },
      { name: 'is_finalized', label: 'Finalize Now', type: 'switch', defaultValue: false }
    ],
    [submissionOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'submission_id', label: 'Submission', render: (row) => submissionLabelById[row.submission_id] || row.submission_id },
      { key: 'student_user_id', label: 'Student', render: (row) => studentLabelById[row.student_user_id] || row.student_user_id },
      { key: 'teacher_user_id', label: 'Teacher', render: (row) => teacherLabelById[row.teacher_user_id] || row.teacher_user_id },
      { key: 'ai_score', label: 'AI Score', render: (row) => (row.ai_score ?? '-') },
      {
        key: 'ai_feedback',
        label: 'AI Feedback',
        render: (row) => {
          const text = row.ai_feedback || '-';
          if (!row.ai_feedback) return text;
          return text.length > 120 ? `${text.slice(0, 120)}...` : text;
        }
      },
      { key: 'internal_total', label: 'Internal' },
      { key: 'grand_total', label: 'Total' },
      { key: 'grade', label: 'Grade' },
      { key: 'is_finalized', label: 'Finalized', render: (row) => (row.is_finalized ? 'Yes' : 'No') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [studentLabelById, submissionLabelById, teacherLabelById]
  );

  const rowActions = useMemo(() => {
    if (!['admin', 'teacher'].includes(user?.role || '')) {
      return [];
    }

    const actions = [
      {
        key: 'open-ai-console',
        label: 'Open AI Console',
        onClick: async (row) => {
          navigate(`/submissions/${row.submission_id}/evaluate`);
        }
      },
      {
        key: 'finalize',
        label: 'Finalize',
        onClick: async (row, { reload, pushToast }) => {
          if (row.is_finalized) {
            pushToast({ title: 'Already finalized', description: 'Evaluation is already finalized.', variant: 'info' });
            return;
          }
          await apiClient.patch(`/evaluations/${row.id}/finalize`);
          pushToast({ title: 'Finalized', description: 'Evaluation finalized successfully.', variant: 'success' });
          await reload();
        }
      }
    ];

    if (user?.role === 'admin') {
      actions.push({
        key: 'override-unfinalize',
        label: 'Unfinalize',
        onClick: async (row, { reload, pushToast }) => {
          const reason = window.prompt('Enter reason for admin override unfinalize:');
          if (!reason || reason.trim().length < 5) {
            pushToast({ title: 'Reason required', description: 'Please enter at least 5 characters.', variant: 'error' });
            return;
          }
          await apiClient.patch(`/evaluations/${row.id}/override-unfinalize`, { reason: reason.trim() });
          pushToast({ title: 'Unlocked', description: 'Evaluation unfinalized by admin override.', variant: 'success' });
          await reload();
        }
      });
    }

    return actions;
  }, [user?.role]);

  const studentSubmissionLabelById = useMemo(
    () => Object.fromEntries(submissions.map((item) => [item.id, item.title || item.original_filename || item.id])),
    [submissions]
  );

  const filteredStudentRows = useMemo(() => {
    return studentRows.filter((row) => {
      const q = studentFilter.query.trim().toLowerCase();
      const matchesFinalized = studentFilter.finalized === '' || String(Boolean(row.is_finalized)) === studentFilter.finalized;
      if (!matchesFinalized) return false;
      if (!q) return true;
      const hay = `${studentSubmissionLabelById[row.submission_id] || row.submission_id || ''} ${row.grade || ''} ${row.remarks || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [studentFilter.finalized, studentFilter.query, studentRows, studentSubmissionLabelById]);

  const studentSummary = useMemo(() => {
    const total = studentRows.length;
    const finalized = studentRows.filter((item) => item.is_finalized).length;
    const avg = total ? (studentRows.reduce((acc, item) => acc + Number(item.grand_total || 0), 0) / total).toFixed(1) : '0.0';
    return { total, finalized, avg };
  }, [studentRows]);

  if (isStudent) {
    const studentColumns = [
      { key: 'submission_id', label: 'Submission', render: (row) => studentSubmissionLabelById[row.submission_id] || row.submission_id },
      { key: 'grand_total', label: 'Total', render: (row) => row.grand_total ?? '-' },
      { key: 'grade', label: 'Grade', render: (row) => row.grade || '-' },
      {
        key: 'is_finalized',
        label: 'Status',
        render: (row) => (
          <Badge variant={row.is_finalized ? 'success' : 'warning'}>
            {row.is_finalized ? 'Finalized' : 'In Progress'}
          </Badge>
        )
      },
      {
        key: 'remarks',
        label: 'Remarks',
        render: (row) => (row.remarks ? (row.remarks.length > 80 ? `${row.remarks.slice(0, 80)}...` : row.remarks) : '-')
      },
      {
        key: 'created_at',
        label: 'Created',
        render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-')
      }
    ];

    return (
      <div className="space-y-5 page-fade">
        <Card className="space-y-2">
          <h1 className="text-2xl font-semibold">My Evaluations</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            View grades, feedback status, and finalized result history.
          </p>
        </Card>

        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Total Evaluations</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.total}</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Finalized</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.finalized}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 size={12} /> Published marks</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Average Score</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.avg}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-brand-600"><BarChart3 size={12} /> Across all evaluations</p>
          </Card>
        </div>

        <Card className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="relative block sm:col-span-2">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                className="input pl-8"
                placeholder="Search by submission, grade, remarks"
                value={studentFilter.query}
                onChange={(e) => setStudentFilter((prev) => ({ ...prev, query: e.target.value }))}
              />
            </label>
            <FormInput
              as="select"
              label="Finalized"
              value={studentFilter.finalized}
              onChange={(e) => setStudentFilter((prev) => ({ ...prev, finalized: e.target.value }))}
            >
              <option value="">All</option>
              <option value="true">Finalized</option>
              <option value="false">In Progress</option>
            </FormInput>
          </div>
          {studentLoading ? <p className="text-sm text-slate-500">Loading evaluations...</p> : null}
          <Table columns={studentColumns} data={filteredStudentRows} />
        </Card>
      </div>
    );
  }

  return (
    <EntityManager
      title="Evaluations"
      endpoint="/evaluations/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      rowActions={rowActions}
      hideCreate={!['admin', 'teacher'].includes(user?.role || '')}
      createTransform={(payload) => ({
        ...payload,
        is_finalized: Boolean(payload.is_finalized),
        remarks: payload.remarks || null
      })}
    />
  );
}
