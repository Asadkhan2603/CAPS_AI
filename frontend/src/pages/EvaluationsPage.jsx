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

function aiStatusVariant(status) {
  if (status === 'completed' || status === 'success') return 'success';
  if (status === 'fallback') return 'warning';
  if (status === 'failed') return 'danger';
  if (status === 'running') return 'info';
  if (status === 'pending' || status === 'queued') return 'warning';
  return 'default';
}

function resultStatusVariant(status) {
  if (status === 'released') return 'success';
  if (status === 'correction_requested') return 'warning';
  if (status === 'reopened') return 'warning';
  if (status === 'finalized_unreleased') return 'warning';
  if (status === 'draft') return 'default';
  return 'info';
}

function resultStatusLabel(status) {
  if (status === 'released') return 'Released';
  if (status === 'correction_requested') return 'Correction Requested';
  if (status === 'reopened') return 'Reopened';
  if (status === 'finalized_unreleased') return 'Finalized';
  if (status === 'draft') return 'Draft';
  return status || 'Draft';
}

function formatHeuristicConfidence(confidence, mode, status) {
  if (mode === 'fallback' || status === 'fallback') {
    return 'Assistive fallback';
  }
  return confidence != null ? `${Math.round(confidence * 100)}% heuristic` : '-';
}

function formatConfidenceMode(mode, status) {
  if (mode === 'fallback' || status === 'fallback') return 'Fallback assistive';
  if (mode === 'provider') return 'Provider';
  return '';
}

export default function EvaluationsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();
  const isStudent = user?.role === 'student';
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [studentRows, setStudentRows] = useState([]);
  const [semesterResults, setSemesterResults] = useState([]);
  const [transcript, setTranscript] = useState(null);
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
  const [marksheetLoading, setMarksheetLoading] = useState(false);
  const [semesterPublishingId, setSemesterPublishingId] = useState('');
  const [gradingPolicy, setGradingPolicy] = useState(null);
  const [gradingPolicySaving, setGradingPolicySaving] = useState(false);

  useEffect(() => {
    async function loadLookups() {
      if (isStudent) {
        try {
          const [submissionsRes, evaluationsRes, semesterResultsRes, transcriptRes] = await Promise.all([
            apiClient.get('/submissions/', { params: { skip: 0, limit: 100 } }),
            apiClient.get('/evaluations/', { params: { skip: 0, limit: 100 } }),
            apiClient.get('/evaluations/results/summary'),
            apiClient.get('/evaluations/results/transcript')
          ]);
          setSubmissions(submissionsRes.data || []);
          setStudentRows(evaluationsRes.data || []);
          setSemesterResults(semesterResultsRes.data || []);
          setTranscript(transcriptRes.data || null);
        } catch {
          setSubmissions([]);
          setStudentRows([]);
          setSemesterResults([]);
          setTranscript(null);
        } finally {
          setStudentLoading(false);
        }
        return;
      }

      try {
        const [submissionsRes, usersRes, gradingPolicyRes] = await Promise.all([
          apiClient.get('/submissions/', { params: { skip: 0, limit: 100 } }),
          user?.role === 'admin' ? apiClient.get('/users/') : Promise.resolve({ data: [] }),
          user?.role === 'admin' ? apiClient.get('/evaluations/results/grading-policy') : Promise.resolve({ data: null })
        ]);
        setSubmissions(submissionsRes.data || []);
        setUsers(usersRes.data || []);
        setGradingPolicy(gradingPolicyRes.data || null);
      } catch {
        setSubmissions([]);
        setUsers([]);
        setGradingPolicy(null);
      }
    }
    if (isStudent) {
      setStudentLoading(true);
    }
    loadLookups();
  }, [isStudent, user?.role]);

  function updateGradingPolicyField(name, value) {
    setGradingPolicy((prev) => ({ ...(prev || {}), [name]: value }));
  }

  function updateGradePoint(grade, value) {
    setGradingPolicy((prev) => ({
      ...(prev || {}),
      grade_points: {
        ...(prev?.grade_points || {}),
        [grade]: Number(value),
      }
    }));
  }

  async function saveGradingPolicy() {
    if (!gradingPolicy || user?.role !== 'admin') return;
    setGradingPolicySaving(true);
    try {
      const response = await apiClient.patch('/evaluations/results/grading-policy', {
        transcript_precision: Number(gradingPolicy.transcript_precision ?? 2),
        grade_points: Object.fromEntries(
          Object.entries(gradingPolicy.grade_points || {}).map(([grade, value]) => [grade, Number(value)])
        )
      });
      setGradingPolicy(response.data || null);
      pushToast({ title: 'Grading policy saved', description: 'Transcript and semester GPA policy updated.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Policy save failed', description: formatApiError(err, 'Unable to save grading policy'), variant: 'error' });
    } finally {
      setGradingPolicySaving(false);
    }
  }

  const submissionOptions = useMemo(
    () =>
      submissions.map((item) => ({
        value: item.id,
        label: item.display_label || `${item.original_filename || 'Submission'} (${item.public_id || item.id})`
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
      {
        key: 'submission_id',
        label: 'Submission',
        render: (row) => row.submission_label || submissionLabelById[row.submission_id] || row.submission_id
      },
      {
        key: 'student_user_id',
        label: 'Student',
        render: (row) => row.student_label || studentLabelById[row.student_user_id] || row.student_user_id
      },
      {
        key: 'teacher_user_id',
        label: 'Teacher',
        render: (row) => row.teacher_label || teacherLabelById[row.teacher_user_id] || row.teacher_user_id
      },
      {
        key: 'ai_status',
        label: 'AI Status',
        render: (row) => (
          <Badge variant={aiStatusVariant(row.ai_status)}>
            {row.ai_status || 'pending'}
          </Badge>
        )
      },
      { key: 'ai_score', label: 'AI Score', render: (row) => (row.ai_score ?? '-') },
      {
        key: 'ai_confidence',
        label: 'Heuristic Confidence',
        render: (row) => {
          const confidence = formatHeuristicConfidence(row.ai_confidence, row.ai_confidence_mode, row.ai_status);
          const modeLabel = formatConfidenceMode(row.ai_confidence_mode, row.ai_status);
          const mode = modeLabel ? ` (${modeLabel})` : '';
          return `${confidence}${mode}`;
        }
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
      {
        key: 'result_status',
        label: 'Result',
        render: (row) => (
          <div className="space-y-1">
            <Badge variant={resultStatusVariant(row.result_status)}>
              {resultStatusLabel(row.result_status)}
            </Badge>
            {row.result_status === 'released' ? (
              <p className="text-[11px] text-slate-500">
                v{row.result_version || 1}
                {row.released_at ? ` | ${new Date(row.released_at).toLocaleString()}` : ''}
              </p>
            ) : null}
          </div>
        )
      },
      { key: 'is_finalized', label: 'Finalized', render: (row) => (row.is_finalized ? 'Yes' : 'No') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    [studentLabelById, submissionLabelById, teacherLabelById]
  );

  async function openTraceViewer(row) {
    setTraceMeta({
      evaluationId: row.id,
      submissionLabel: row.submission_label || submissionLabelById[row.submission_id] || row.submission_id
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
      },
      {
        key: 'release-result',
        label: 'Release Result',
        onClick: async (row, { reload, pushToast }) => {
          if (!row.is_finalized) {
            pushToast({ title: 'Finalize first', description: 'Only finalized evaluations can be released.', variant: 'warning' });
            return;
          }
          if (row.result_status === 'released') {
            pushToast({ title: 'Already released', description: 'This official result version is already released.', variant: 'info' });
            return;
          }
          await apiClient.patch(`/evaluations/${row.id}/release`);
          pushToast({ title: 'Result released', description: 'Official result status was published for this evaluation.', variant: 'success' });
          await reload();
        }
      },
      {
        key: 'publish-semester-result',
        label: (row) => (semesterPublishingId === row.id ? 'Publishing...' : 'Publish Semester Result'),
        hidden: (row) => row.result_status !== 'released',
        disabled: (row) => semesterPublishingId === row.id,
        onClick: async (row, { pushToast }) => {
          setSemesterPublishingId(row.id);
          try {
            await apiClient.post(`/evaluations/results/publish-from-evaluation/${row.id}`);
            pushToast({
              title: 'Semester result published',
              description: 'Official semester result record created from released evaluations.',
              variant: 'success'
            });
          } catch (err) {
            pushToast({
              title: 'Semester publish failed',
              description: formatApiError(err, 'Unable to publish semester result'),
              variant: 'error'
            });
          } finally {
            setSemesterPublishingId('');
          }
        }
      },
      {
        key: 'request-result-correction',
        label: 'Request Result Correction',
        hidden: (row) => row.result_status !== 'released',
        onClick: async (row, { pushToast }) => {
          const reason = window.prompt('Why does this released semester result need correction?');
          if (!reason || reason.trim().length < 5) {
            pushToast({
              title: 'Reason required',
              description: 'Enter at least 5 characters to request correction.',
              variant: 'warning'
            });
            return;
          }
          await apiClient.post(`/evaluations/results/request-correction-from-evaluation/${row.id}`, {
            reason: reason.trim()
          });
          pushToast({
            title: 'Correction requested',
            description: 'The linked semester result has been flagged for governed review.',
            variant: 'success'
          });
        }
      }
    ];

    if (user?.role === 'admin') {
      actions.push({
        key: 'open-marksheet',
        label: 'Open Marksheet',
        hidden: (row) => row.result_status !== 'released',
        onClick: async (row, { pushToast }) => {
          if (!row.student_user_id) {
            pushToast({ title: 'Missing student', description: 'This evaluation has no linked student.', variant: 'error' });
            return;
          }
          await openOfficialMarksheet(row.student_user_id);
        }
      });
      actions.push({
        key: 'open-transcript',
        label: 'Open Transcript',
        hidden: (row) => !row.student_user_id,
        onClick: async (row, { pushToast }) => {
          if (!row.student_user_id) {
            pushToast({ title: 'Missing student', description: 'This evaluation has no linked student.', variant: 'error' });
            return;
          }
          await openTranscript(row.student_user_id);
        }
      });
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
  }, [navigate, pushToast, semesterPublishingId, traceMeta?.evaluationId, traceModalOpen, user?.role]);

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
    const released = studentRows.filter((item) => item.result_status === 'released').length;
    return { total, finalized, avg, released };
  }, [studentRows]);

  const transcriptSummary = useMemo(
    () => ({
      semesters: transcript?.semester_count || semesterResults.length,
      cgpa: transcript?.cgpa ?? 0
    }),
    [semesterResults.length, transcript]
  );

  async function openOfficialMarksheet(studentUserId = null) {
    setMarksheetLoading(true);
    try {
      const response = await apiClient.get('/evaluations/results/marksheet', {
        params: studentUserId ? { student_user_id: studentUserId } : undefined
      });
      const marksheet = response.data;
      const popup = window.open('', '_blank', 'noopener,noreferrer,width=1100,height=800');
      if (!popup) {
        pushToast({ title: 'Popup blocked', description: 'Allow popups to open the official marksheet.', variant: 'warning' });
        return;
      }

      const rowsHtml = (marksheet.items || [])
        .map(
          (item, index) => `
            <tr>
              <td>${index + 1}</td>
              <td>${item.submission_label || item.submission_id}</td>
              <td>${item.attendance_percent}%</td>
              <td>${item.internal_total}</td>
              <td>${item.final_exam}</td>
              <td>${item.grand_total}</td>
              <td>${item.grade}</td>
              <td>${item.result_version || 1}</td>
            </tr>`
        )
        .join('');

      popup.document.write(`
        <html>
          <head>
            <title>Official Marksheet${marksheet.student_name ? ` - ${marksheet.student_name}` : ''}</title>
            <style>
              body { font-family: Georgia, serif; margin: 32px; color: #0f172a; }
              h1, h2, p { margin: 0 0 12px; }
              .meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 24px; margin: 20px 0 28px; }
              .summary { display: flex; gap: 24px; margin: 20px 0; font-weight: 600; }
              table { width: 100%; border-collapse: collapse; margin-top: 18px; }
              th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: left; font-size: 14px; }
              th { background: #e2e8f0; }
              .footer { margin-top: 28px; font-size: 12px; color: #475569; }
            </style>
          </head>
          <body>
            <h1>Official Marksheet</h1>
            <p>Generated from released academic results only.</p>
            <div class="meta">
              <div><strong>Student:</strong> ${marksheet.student_name || '-'}</div>
              <div><strong>Roll Number:</strong> ${marksheet.roll_number || '-'}</div>
              <div><strong>Email:</strong> ${marksheet.email || '-'}</div>
              <div><strong>Generated At:</strong> ${new Date(marksheet.generated_at).toLocaleString()}</div>
            </div>
            <div class="summary">
              <div>Released Results: ${marksheet.released_results_count || 0}</div>
              <div>Average Score: ${marksheet.average_score ?? 0}</div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Submission</th>
                  <th>Attendance</th>
                  <th>Internal</th>
                  <th>Final Exam</th>
                  <th>Total</th>
                  <th>Grade</th>
                  <th>Version</th>
                </tr>
              </thead>
              <tbody>
                ${rowsHtml || '<tr><td colspan="8">No released results are available yet.</td></tr>'}
              </tbody>
            </table>
            <p class="footer">This document reflects the current released result versions available in the system.</p>
          </body>
        </html>
      `);
      popup.document.close();
      pushToast({
        title: 'Marksheet ready',
        description: `${marksheet.student_name || 'Official'} marksheet opened in a new window.`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Marksheet failed',
        description: formatApiError(err, 'Unable to load official marksheet'),
        variant: 'error'
      });
    } finally {
      setMarksheetLoading(false);
    }
  }

  async function openTranscript(studentUserId = null) {
    try {
      const response = await apiClient.get('/evaluations/results/transcript', {
        params: studentUserId ? { student_user_id: studentUserId } : undefined
      });
      const transcriptDoc = response.data;
      const popup = window.open('', '_blank', 'noopener,noreferrer,width=1100,height=800');
      if (!popup) {
        pushToast({ title: 'Popup blocked', description: 'Allow popups to open the official transcript.', variant: 'warning' });
        return;
      }

      const rowsHtml = (transcriptDoc.semesters || [])
        .map(
          (item, index) => `
            <tr>
              <td>${index + 1}</td>
              <td>${item.semester_label || item.semester_id || '-'}</td>
              <td>${item.result_count ?? 0}</td>
              <td>${item.average_score ?? 0}</td>
              <td>${item.gpa ?? 0}</td>
              <td>${item.cgpa ?? 0}</td>
              <td>${item.result_version || 1}</td>
              <td>${item.status || 'released'}</td>
            </tr>`
        )
        .join('');

      popup.document.write(`
        <html>
          <head>
            <title>Academic Transcript${transcriptDoc.student_name ? ` - ${transcriptDoc.student_name}` : ''}</title>
            <style>
              body { font-family: Georgia, serif; margin: 32px; color: #0f172a; }
              h1, h2, p { margin: 0 0 12px; }
              .meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 24px; margin: 20px 0 28px; }
              .summary { display: flex; gap: 24px; margin: 20px 0; font-weight: 600; }
              table { width: 100%; border-collapse: collapse; margin-top: 18px; }
              th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: left; font-size: 14px; }
              th { background: #e2e8f0; }
              .footer { margin-top: 28px; font-size: 12px; color: #475569; }
            </style>
          </head>
          <body>
            <h1>Academic Transcript</h1>
            <p>Generated from published semester result records only.</p>
            <div class="meta">
              <div><strong>Student:</strong> ${transcriptDoc.student_name || '-'}</div>
              <div><strong>Roll Number:</strong> ${transcriptDoc.roll_number || '-'}</div>
              <div><strong>Email:</strong> ${transcriptDoc.email || '-'}</div>
              <div><strong>Generated At:</strong> ${new Date(transcriptDoc.generated_at).toLocaleString()}</div>
            </div>
            <div class="summary">
              <div>Published Semesters: ${transcriptDoc.semester_count || 0}</div>
              <div>CGPA: ${transcriptDoc.cgpa ?? 0}</div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Semester</th>
                  <th>Released Items</th>
                  <th>Average</th>
                  <th>GPA</th>
                  <th>CGPA</th>
                  <th>Version</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${rowsHtml || '<tr><td colspan="8">No published semester results are available yet.</td></tr>'}
              </tbody>
            </table>
            <p class="footer">This transcript reflects the currently published semester result records available in the system.</p>
          </body>
        </html>
      `);
      popup.document.close();
      pushToast({
        title: 'Transcript ready',
        description: `${transcriptDoc.student_name || 'Academic'} transcript opened in a new window.`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Transcript failed',
        description: formatApiError(err, 'Unable to load academic transcript'),
        variant: 'error'
      });
    }
  }

  if (isStudent) {
    const studentColumns = [
      { key: 'submission_id', label: 'Submission', render: (row) => studentSubmissionLabelById[row.submission_id] || row.submission_id },
      { key: 'grand_total', label: 'Total', render: (row) => row.grand_total ?? '-' },
      { key: 'grade', label: 'Grade', render: (row) => row.grade || '-' },
      {
        key: 'result_status',
        label: 'Result',
        render: (row) => (
          <div className="space-y-1">
            <Badge variant={resultStatusVariant(row.result_status)}>
              {resultStatusLabel(row.result_status)}
            </Badge>
            <p className="text-[11px] text-slate-500">
              {row.result_status === 'released'
                ? `Official result${row.result_version ? ` v${row.result_version}` : ''}`
                : row.is_finalized
                  ? 'Awaiting official release'
                  : 'Still being reviewed'}
            </p>
          </div>
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
            View grades, review progress, and officially released result history.
          </p>
          <p className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-200">
            Finalized evaluations can still wait for official release. Only rows marked as released should be treated as the official published result. Internal AI scoring signals are intentionally not shown in the student evaluation view.
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
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 size={12} /> Ready or published</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Released</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.released}</p>
            <button type="button" className="btn-secondary mt-3" onClick={openOfficialMarksheet} disabled={marksheetLoading}>
              {marksheetLoading ? 'Opening...' : 'Open Marksheet'}
            </button>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Average Score</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.avg}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-brand-600"><BarChart3 size={12} /> Across all evaluations</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Published Semesters</p>
            <p className="mt-1 text-3xl font-bold">{transcriptSummary.semesters}</p>
            <p className="mt-1 text-xs text-slate-500">Official semester result records</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">CGPA</p>
            <p className="mt-1 text-3xl font-bold">{transcriptSummary.cgpa}</p>
            <p className="mt-1 text-xs text-slate-500">From published semester results</p>
            <button type="button" className="btn-secondary mt-3" onClick={() => openTranscript()}>
              Open Transcript
            </button>
          </Card>
        </div>

        <Card className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold">Semester Results & Transcript</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Official semester records generated from released results appear here.
            </p>
          </div>
          <Table
            columns={[
              { key: 'semester_label', label: 'Semester', render: (row) => row.semester_label || row.semester_id || '-' },
              { key: 'result_count', label: 'Released Items' },
              { key: 'average_score', label: 'Average' },
              { key: 'gpa', label: 'GPA' },
              { key: 'cgpa', label: 'CGPA', render: (row) => row.cgpa ?? '-' },
              {
                key: 'status',
                label: 'Status',
                render: (row) => (
                  <Badge variant={row.status === 'released' ? 'success' : row.status === 'reopened' ? 'warning' : 'default'}>
                    {row.status || 'released'}
                  </Badge>
                )
              }
            ]}
            data={transcript?.semesters || []}
          />
        </Card>

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
      <Card className="space-y-2">
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Teacher/Admin AI review policy</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          `fallback` indicates backup grading guidance was used instead of the primary provider. Treat fallback output as assistive input and confirm final marks before publishing.
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Heuristic confidence is a consistency signal for reviewers, not a calibrated probability that the AI is correct.
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          `Finalized` means the evaluator locked the marking record. `Released` means the official result status has been published for student consumption.
        </p>
      </Card>
      {user?.role === 'admin' && gradingPolicy ? (
        <Card className="space-y-3">
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Official Result GPA Policy</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              These settings affect semester GPA and transcript CGPA calculations from published result records.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            {Object.entries(gradingPolicy.grade_points || {}).map(([grade, value]) => (
              <FormInput
                key={grade}
                label={`${grade} Grade Point`}
                type="number"
                min="0"
                max="4"
                step="0.1"
                value={value}
                onChange={(event) => updateGradePoint(grade, event.target.value)}
              />
            ))}
          </div>
          <div className="grid gap-3 md:grid-cols-[220px_auto] md:items-end">
            <FormInput
              label="Transcript Precision"
              type="number"
              min="0"
              max="4"
              value={gradingPolicy.transcript_precision ?? 2}
              onChange={(event) => updateGradingPolicyField('transcript_precision', event.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-primary" onClick={saveGradingPolicy} disabled={gradingPolicySaving}>
                {gradingPolicySaving ? 'Saving...' : 'Save GPA Policy'}
              </button>
            </div>
          </div>
        </Card>
      ) : null}

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
                  {item.ai_score ?? '-'} | Heuristic Confidence:{' '}
                  {formatHeuristicConfidence(item.ai_confidence, item.ai_confidence_mode, item.ai_status)}
                  {(item.ai_confidence_mode || item.ai_status) ? ` (${formatConfidenceMode(item.ai_confidence_mode, item.ai_status)})` : ''}
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
