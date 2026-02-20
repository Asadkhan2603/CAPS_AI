import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

export default function EvaluationsPage() {
  const { user } = useAuth();
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);

  useEffect(() => {
    async function loadLookups() {
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
    loadLookups();
  }, []);

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
