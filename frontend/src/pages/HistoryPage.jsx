import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { formatApiError } from '../utils/apiError';

export default function HistoryPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [registrationRows, setRegistrationRows] = useState([]);
  const [submissionRows, setSubmissionRows] = useState([]);
  const [evaluationRows, setEvaluationRows] = useState([]);
  const [notificationRows, setNotificationRows] = useState([]);

  async function loadHistory() {
    setLoading(true);
    setError('');
    try {
      const [registrationsRes, submissionsRes, evaluationsRes, notificationsRes] = await Promise.all([
        apiClient.get('/event-registrations/', { params: { skip: 0, limit: 50 } }),
        apiClient.get('/submissions/', { params: { skip: 0, limit: 50 } }),
        apiClient.get('/evaluations/', { params: { skip: 0, limit: 50 } }),
        apiClient.get('/notifications/', { params: { skip: 0, limit: 50 } })
      ]);

      setRegistrationRows(registrationsRes.data || []);
      setSubmissionRows(submissionsRes.data || []);
      setEvaluationRows(evaluationsRes.data || []);
      setNotificationRows(notificationsRes.data || []);
    } catch (err) {
      setError(formatApiError(err, 'Failed to load history logs'));
      setRegistrationRows([]);
      setSubmissionRows([]);
      setEvaluationRows([]);
      setNotificationRows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  const registrationColumns = useMemo(
    () => [
      { key: 'event_id', label: 'Event ID' },
      { key: 'full_name', label: 'Student', render: (row) => row.full_name || row.student_name || '-' },
      { key: 'status', label: 'Status' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  const submissionColumns = useMemo(
    () => [
      { key: 'assignment_id', label: 'Assignment ID' },
      { key: 'original_filename', label: 'File' },
      { key: 'status', label: 'Status' },
      { key: 'ai_status', label: 'AI Status' },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  const evaluationColumns = useMemo(
    () => [
      { key: 'submission_id', label: 'Submission ID' },
      { key: 'grand_total', label: 'Total' },
      { key: 'grade', label: 'Grade' },
      { key: 'is_finalized', label: 'Finalized', render: (row) => (row.is_finalized ? 'Yes' : 'No') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  const notificationColumns = useMemo(
    () => [
      { key: 'title', label: 'Title' },
      { key: 'priority', label: 'Priority' },
      { key: 'scope', label: 'Scope' },
      { key: 'is_read', label: 'Read', render: (row) => (row.is_read ? 'Yes' : 'No') },
      { key: 'created_at', label: 'Created At', render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-') }
    ],
    []
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold">History Logs</h1>
          <button className="btn-secondary" onClick={loadHistory}>Refresh</button>
        </div>
        {loading ? <p className="text-sm text-slate-500">Loading logs...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Registration Records</h2>
        <Table columns={registrationColumns} data={registrationRows} />
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Assignment Submission Log</h2>
        <Table columns={submissionColumns} data={submissionRows} />
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Evaluation Logs</h2>
        <Table columns={evaluationColumns} data={evaluationRows} />
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Notifications Log</h2>
        <Table columns={notificationColumns} data={notificationRows} />
      </Card>
    </div>
  );
}
