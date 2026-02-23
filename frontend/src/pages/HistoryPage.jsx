import { useEffect, useMemo, useState } from 'react';
import { Bell, CalendarClock, ClipboardList, History, Search, Trophy } from 'lucide-react';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import { formatApiError } from '../utils/apiError';
import { useAuth } from '../hooks/useAuth';

export default function HistoryPage() {
  const { user } = useAuth();
  const isStudent = user?.role === 'student';
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [registrationRows, setRegistrationRows] = useState([]);
  const [submissionRows, setSubmissionRows] = useState([]);
  const [evaluationRows, setEvaluationRows] = useState([]);
  const [notificationRows, setNotificationRows] = useState([]);
  const [query, setQuery] = useState('');
  const [section, setSection] = useState('all');

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

  const studentSummary = useMemo(() => {
    return {
      registrations: registrationRows.length,
      submissions: submissionRows.length,
      evaluations: evaluationRows.length,
      unreadNotifications: notificationRows.filter((item) => !item.is_read).length
    };
  }, [evaluationRows.length, notificationRows, registrationRows.length, submissionRows.length]);

  const filteredSubmissionRows = useMemo(() => {
    if (!query.trim()) return submissionRows;
    const q = query.toLowerCase();
    return submissionRows.filter((item) => `${item.original_filename || ''} ${item.assignment_id || ''} ${item.status || ''}`.toLowerCase().includes(q));
  }, [query, submissionRows]);

  const filteredEvaluationRows = useMemo(() => {
    if (!query.trim()) return evaluationRows;
    const q = query.toLowerCase();
    return evaluationRows.filter((item) => `${item.submission_id || ''} ${item.grade || ''} ${item.remarks || ''}`.toLowerCase().includes(q));
  }, [evaluationRows, query]);

  const filteredNotificationRows = useMemo(() => {
    if (!query.trim()) return notificationRows;
    const q = query.toLowerCase();
    return notificationRows.filter((item) => `${item.title || ''} ${item.message || ''} ${item.scope || ''}`.toLowerCase().includes(q));
  }, [notificationRows, query]);

  if (isStudent) {
    return (
      <div className="space-y-5 page-fade">
        <Card className="space-y-2">
          <h1 className="inline-flex items-center gap-2 text-2xl font-semibold"><History size={22} /> Activity History</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Your timeline across submissions, evaluations, notifications, and event registrations.</p>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Registrations</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.registrations}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-brand-600"><CalendarClock size={12} /> Club / event history</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Submissions</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.submissions}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-600"><ClipboardList size={12} /> Assignment uploads</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Evaluations</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.evaluations}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-indigo-600"><Trophy size={12} /> Marked results</p>
          </Card>
          <Card className="!p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Unread Alerts</p>
            <p className="mt-1 text-3xl font-bold">{studentSummary.unreadNotifications}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-amber-600"><Bell size={12} /> Needs attention</p>
          </Card>
        </div>

        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="relative block w-full max-w-md">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input className="input pl-8" placeholder="Search all history" value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            <FormInput as="select" label="Section" value={section} onChange={(e) => setSection(e.target.value)} className="max-w-[220px]">
              <option value="all">All</option>
              <option value="registrations">Registrations</option>
              <option value="submissions">Submissions</option>
              <option value="evaluations">Evaluations</option>
              <option value="notifications">Notifications</option>
            </FormInput>
            <button className="btn-secondary" onClick={loadHistory}>Refresh</button>
          </div>
          {loading ? <p className="text-sm text-slate-500">Loading logs...</p> : null}
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        </Card>

        {(section === 'all' || section === 'registrations') ? (
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Event Registrations</h2>
            <Table columns={registrationColumns} data={registrationRows} />
          </Card>
        ) : null}

        {(section === 'all' || section === 'submissions') ? (
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Submissions</h2>
            <Table columns={submissionColumns} data={filteredSubmissionRows} />
          </Card>
        ) : null}

        {(section === 'all' || section === 'evaluations') ? (
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Evaluations</h2>
            <Table columns={evaluationColumns} data={filteredEvaluationRows} />
          </Card>
        ) : null}

        {(section === 'all' || section === 'notifications') ? (
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Notifications</h2>
            <Table columns={notificationColumns} data={filteredNotificationRows} />
          </Card>
        ) : null}
      </div>
    );
  }

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
