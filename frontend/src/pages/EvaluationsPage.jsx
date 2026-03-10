import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, CheckCircle2, Search } from 'lucide-react';
import EntityManager from '../components/ui/EntityManager';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import FormInput from '../components/ui/FormInput';
import Modal from '../components/ui/Modal';
import { apiClient } from '../services/apiClient';
import { getEvaluationTrace, refreshEvaluationAi } from '../services/aiService';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

function formatTraceTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export default function EvaluationsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();
  const isStudent = user?.role === 'student';
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [studentRows, setStudentRows] = useState([]);
  const [studentLoading, setStudentLoading] = useState(false);
  const [studentFilter, setStudentFilter] = useState({ finalized: '', query: '' });
  const [traceModalOpen, setTraceModalOpen] = useState(false);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceMeta, setTraceMeta] = useState(null);
  const [traceItems, setTraceItems] = useState([]);
  const [unfinalizeModalOpen, setUnfinalizeModalOpen] = useState(false);
  const [unfinalizeReason, setUnfinalizeReason] = useState('');
  const [unfinalizeContext, setUnfinalizeContext] = useState(null);
  const [unfinalizeSubmitting, setUnfinalizeSubmitting] = useState(false);

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

  const scoringFields = useMemo(
    () => [
      { name: 'submission_id', label: 'Submission', type: 'select', options: submissionOptions, required: true },
      { name: 'attendance_percent', label: 'Attendance %', type: 'number', min: 0, max: 100, required: true, defaultValue: 85 },
      { name: 'skill', label: 'Skill (0-2.5)', type: 'number', min: 0, max: 2.5, required: true, defaultValue: 2 },
      { name: 'behavior', label: 'Behavior (0-2.5)', type: 'number', min: 0, max: 2.5, required: true, defaultValue: 2 },
      { name: 'report', label: 'Report (0-10)', type: 'number', min: 0, max: 10, required: true, defaultValue: 8 },
      { name: 'viva', label: 'Viva (0-20)', type: 'number', min: 0, max: 20, required: true, defaultValue: 15 },
      { name: 'final_exam', label: 'Final Exam (0-60)', type: 'number', min: 0, max: 60, required: true, defaultValue: 40 },
      { name: 'remarks', label: 'Remarks', nullable: true }
    ],
    [submissionOptions]
  );
  const createFields = useMemo(
    () => [...scoringFields, { name: 'is_finalized', label: 'Finalize Now', type: 'switch', defaultValue: false }],
    [scoringFields]
  );
  const editFields = useMemo(
    () => [
      ...scoringFields,
      { name: 'is_finalized', label: 'Finalized', type: 'switch', defaultValue: false }
    ],
    [scoringFields]
  );

  const columns = useMemo(
    () => [
      { key: 'submission_id', label: 'Submission', render: (row) => submissionLabelById[row.submission_id] || row.submission_id },
      { key: 'student_user_id', label: 'Student', render: (row) => studentLabelById[row.student_user_id] || row.student_user_id },
      { key: 'teacher_user_id', label: 'Teacher', render: (row) => teacherLabelById[row.teacher_user_id] || row.teacher_user_id },
      {
        key: 'ai_status',
        label: 'AI Status',
        render: (row) => (
          <Badge variant={row.ai_status === 'success' ? 'success' : row.ai_status === 'fallback' ? 'warning' : 'default'}>
            {row.ai_status || 'pending'}
          </Badge>
        )
      },
      { key: 'ai_score', label: 'AI Score', render: (row) => (row.ai_score ?? '-') },
      {
        key: 'ai_confidence',
        label: 'Confidence',
        render: (row) => (row.ai_confidence != null ? `${Math.round(row.ai_confidence * 100)}%` : '-')
      },
      {
        key: 'ai_risk_flags',
        label: 'Risk Flags',
        render: (row) => ((row.ai_risk_flags || []).length ? row.ai_risk_flags.join(', ') : '-')
      },
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

  async function openTraceViewer(row) {
    setTraceMeta({
      evaluationId: row.id,
      submissionLabel: submissionLabelById[row.submission_id] || row.submission_id
    });
    setTraceItems([]);
    setTraceModalOpen(true);
    setTraceLoading(true);
    try {
      const response = await getEvaluationTrace(row.id, { limit: 10 });
      setTraceItems(response?.items || []);
    } catch (err) {
      pushToast({
        title: 'Trace failed',
        description: formatApiError(err, 'Unable to load evaluation AI trace'),
        variant: 'error'
      });
    } finally {
      setTraceLoading(false);
    }
  }

  function openUnfinalizeModal(row, reload) {
    setUnfinalizeContext({ row, reload });
    setUnfinalizeReason('');
    setUnfinalizeModalOpen(true);
  }

  async function onConfirmUnfinalize() {
    if (!unfinalizeContext?.row) return;
    const reason = unfinalizeReason.trim();
    if (reason.length < 5) {
      pushToast({ title: 'Reason required', description: 'Please enter at least 5 characters.', variant: 'error' });
      return;
    }
    setUnfinalizeSubmitting(true);
    try {
      await apiClient.patch(`/evaluations/${unfinalizeContext.row.id}/override-unfinalize`, { reason });
      pushToast({ title: 'Unlocked', description: 'Evaluation unfinalized by admin override.', variant: 'success' });
      setUnfinalizeModalOpen(false);
      setUnfinalizeContext(null);
      await unfinalizeContext.reload?.();
    } catch (err) {
      pushToast({
        title: 'Unfinalize failed',
        description: formatApiError(err, 'Failed to unfinalize evaluation'),
        variant: 'error'
      });
    } finally {
      setUnfinalizeSubmitting(false);
    }
  }

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
        key: 'view-trace',
        label: 'View Trace',
        onClick: async (row) => {
          await openTraceViewer(row);
        }
      },
      {
        key: 'refresh-ai',
        label: 'Refresh AI',
        onClick: async (row, { reload, pushToast: rowToast }) => {
          await refreshEvaluationAi(row.id);
          rowToast({ title: 'AI refreshed', description: 'Stored AI insight was refreshed.', variant: 'success' });
          await reload();
          if (traceModalOpen && traceMeta?.evaluationId === row.id) {
            await openTraceViewer(row);
          }
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
          openUnfinalizeModal(row, reload);
          pushToast({
            title: 'Override requested',
            description: 'Provide a reason to reopen this finalized evaluation.',
            variant: 'info'
          });
        }
      });
    }

    return actions;
  }, [navigate, submissionLabelById, traceMeta?.evaluationId, traceModalOpen, user?.role]);

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
    <>
      <EntityManager
        title="Evaluations"
        endpoint="/evaluations/"
        filters={filters}
        createFields={createFields}
        editFields={editFields}
        columns={columns}
        rowActions={rowActions}
        enableEdit
        hideCreate={!['admin', 'teacher'].includes(user?.role || '')}
        createTransform={(payload) => ({
          ...payload,
          is_finalized: Boolean(payload.is_finalized),
          remarks: payload.remarks || null
        })}
        updateTransform={(payload) => ({
          ...payload,
          is_finalized: Boolean(payload.is_finalized),
          remarks: payload.remarks || null
        })}
      />

      <Modal
        open={traceModalOpen}
        title={traceMeta ? `Evaluation AI Trace: ${traceMeta.submissionLabel}` : 'Evaluation AI Trace'}
        onClose={() => setTraceModalOpen(false)}
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Stored AI run history for evaluation {traceMeta?.evaluationId || '-'}.
          </p>
          {traceLoading ? <p className="text-sm text-slate-500">Loading trace...</p> : null}
          {!traceLoading && traceItems.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No AI trace records found yet.</p>
          ) : null}
          <div className="max-h-[60vh] space-y-2 overflow-y-auto">
            {traceItems.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {formatTraceTimestamp(item.created_at)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Status: {item.ai_status || '-'} | Provider: {item.ai_provider || '-'}
                  </p>
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                  Grade: {item.grade || '-'} | Total: {item.grand_total ?? '-'} | Internal: {item.internal_total ?? '-'} | AI Score:{' '}
                  {item.ai_score ?? '-'} | Confidence:{' '}
                  {item.ai_confidence != null ? `${Math.round(item.ai_confidence * 100)}%` : '-'}
                </p>
                {(item.ai_risk_flags || []).length ? (
                  <p className="mt-2 text-xs text-rose-700 dark:text-rose-300">
                    Risk Flags: {(item.ai_risk_flags || []).join(' | ')}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </Modal>

      <Modal
        open={unfinalizeModalOpen}
        title="Admin Override Unfinalize"
        onClose={() => {
          if (unfinalizeSubmitting) return;
          setUnfinalizeModalOpen(false);
          setUnfinalizeContext(null);
          setUnfinalizeReason('');
        }}
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Reopening a finalized evaluation is an administrative override. Capture the reason before proceeding.
          </p>
          {unfinalizeContext?.row ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
              Evaluation: {submissionLabelById[unfinalizeContext.row.submission_id] || unfinalizeContext.row.submission_id}
            </div>
          ) : null}
          <FormInput
            as="textarea"
            label="Reason"
            value={unfinalizeReason}
            onChange={(event) => setUnfinalizeReason(event.target.value)}
            placeholder="Enter the reason for reopening this evaluation"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setUnfinalizeModalOpen(false);
                setUnfinalizeContext(null);
                setUnfinalizeReason('');
              }}
              disabled={unfinalizeSubmitting}
            >
              Cancel
            </button>
            <button type="button" className="btn-primary" onClick={onConfirmUnfinalize} disabled={unfinalizeSubmitting}>
              {unfinalizeSubmitting ? 'Submitting...' : 'Confirm'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
