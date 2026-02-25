import { useEffect, useMemo, useState } from 'react';
import Card from '../../components/ui/Card';
import Table from '../../components/ui/Table';
import EmptyState from '../../components/ui/EmptyState';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { formatApiError } from '../../utils/apiError';
import { useToast } from '../../hooks/useToast';
import {
  createGovernanceReview,
  decideGovernanceReview,
  fetchGovernanceDashboard,
  fetchGovernancePolicy,
  fetchGovernanceReviews,
  fetchGovernanceSessions,
  updateGovernancePolicy
} from '../../services/adminGovernanceApi';

const reviewTypeOptions = [
  { value: 'destructive', label: 'Destructive Action' },
  { value: 'role_change', label: 'Role Change' }
];

export default function AdminGovernancePage() {
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [error, setError] = useState('');
  const [policy, setPolicy] = useState({
    two_person_rule_enabled: false,
    role_change_approval_enabled: false,
    retention_days_audit: 365,
    retention_days_sessions: 90
  });
  const [dashboard, setDashboard] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [reviewFilter, setReviewFilter] = useState('');
  const [sessions, setSessions] = useState([]);
  const [sessionFilter, setSessionFilter] = useState('active');
  const [createReviewForm, setCreateReviewForm] = useState({
    review_type: 'destructive',
    action: '',
    entity_type: '',
    entity_id: '',
    reason: ''
  });

  const metrics = useMemo(
    () => [
      { label: 'Pending Reviews', value: dashboard?.pending_reviews ?? 0 },
      { label: 'Approved (24h)', value: dashboard?.approved_reviews_24h ?? 0 },
      { label: 'Login Anomalies (24h)', value: dashboard?.login_anomalies_24h ?? 0 },
      { label: 'Locked Accounts', value: dashboard?.locked_accounts ?? 0 }
    ],
    [dashboard]
  );

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      setError('');
      try {
        const [policyData, dashboardData, reviewData, sessionData] = await Promise.all([
          fetchGovernancePolicy(),
          fetchGovernanceDashboard(),
          fetchGovernanceReviews({ status: reviewFilter || undefined, limit: 100 }),
          fetchGovernanceSessions({ status: sessionFilter || undefined, limit: 50 })
        ]);
        setPolicy((prev) => ({ ...prev, ...policyData }));
        setDashboard(dashboardData);
        setReviews(reviewData);
        setSessions(sessionData.items || []);
      } catch (err) {
        setError(formatApiError(err, 'Failed to load governance data'));
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, []);

  async function reloadDashboard() {
    try {
      const [dashboardData, policyData] = await Promise.all([fetchGovernanceDashboard(), fetchGovernancePolicy()]);
      setDashboard(dashboardData);
      setPolicy((prev) => ({ ...prev, ...policyData }));
    } catch (err) {
      pushToast({ title: 'Refresh failed', description: formatApiError(err, 'Failed to refresh dashboard'), variant: 'error' });
    }
  }

  async function loadReviews(status = reviewFilter) {
    setLoadingReviews(true);
    try {
      const rows = await fetchGovernanceReviews({ status: status || undefined, limit: 100 });
      setReviews(rows);
    } catch (err) {
      pushToast({ title: 'Reviews load failed', description: formatApiError(err, 'Failed to load reviews'), variant: 'error' });
    } finally {
      setLoadingReviews(false);
    }
  }

  async function loadSessions(status = sessionFilter) {
    setLoadingSessions(true);
    try {
      const rows = await fetchGovernanceSessions({ status: status || undefined, limit: 50 });
      setSessions(rows.items || []);
    } catch (err) {
      pushToast({ title: 'Sessions load failed', description: formatApiError(err, 'Failed to load sessions'), variant: 'error' });
    } finally {
      setLoadingSessions(false);
    }
  }

  async function onSavePolicy() {
    setSavingPolicy(true);
    try {
      const next = await updateGovernancePolicy({
        two_person_rule_enabled: policy.two_person_rule_enabled,
        role_change_approval_enabled: policy.role_change_approval_enabled,
        retention_days_audit: Number(policy.retention_days_audit),
        retention_days_sessions: Number(policy.retention_days_sessions)
      });
      setPolicy((prev) => ({ ...prev, ...next }));
      pushToast({ title: 'Policy updated', description: 'Governance policy saved.', variant: 'success' });
      await reloadDashboard();
    } catch (err) {
      pushToast({ title: 'Policy update failed', description: formatApiError(err, 'Failed to save policy'), variant: 'error' });
    } finally {
      setSavingPolicy(false);
    }
  }

  async function onCreateReview(event) {
    event.preventDefault();
    try {
      await createGovernanceReview({
        review_type: createReviewForm.review_type,
        action: createReviewForm.action.trim(),
        entity_type: createReviewForm.entity_type.trim(),
        entity_id: createReviewForm.entity_id.trim() || null,
        reason: createReviewForm.reason.trim() || null
      });
      pushToast({ title: 'Review created', description: 'Approval request submitted.', variant: 'success' });
      setCreateReviewForm({
        review_type: createReviewForm.review_type,
        action: '',
        entity_type: '',
        entity_id: '',
        reason: ''
      });
      await Promise.all([loadReviews(), reloadDashboard()]);
    } catch (err) {
      pushToast({ title: 'Create review failed', description: formatApiError(err, 'Failed to create review'), variant: 'error' });
    }
  }

  async function onReviewDecision(row, approve) {
    try {
      await decideGovernanceReview(row.id, { approve, note: approve ? 'Approved in admin panel' : 'Rejected in admin panel' });
      pushToast({ title: approve ? 'Review approved' : 'Review rejected', description: `Review ${row.id} updated.`, variant: 'success' });
      await Promise.all([loadReviews(), reloadDashboard()]);
    } catch (err) {
      pushToast({ title: 'Decision failed', description: formatApiError(err, 'Failed to update review'), variant: 'error' });
    }
  }

  const reviewColumns = [
    { key: 'review_type', label: 'Type' },
    { key: 'action', label: 'Action' },
    { key: 'entity_type', label: 'Entity' },
    { key: 'status', label: 'Status' },
    { key: 'requested_by', label: 'Requested By' },
    {
      key: 'created_at',
      label: 'Created',
      render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-')
    }
  ];

  const sessionColumns = [
    { key: 'user_name', label: 'User', render: (row) => row.user_name || row.user_email || row.user_id || '-' },
    {
      key: 'status',
      label: 'Status',
      render: (row) => (
        <span
          className={`rounded-full px-2 py-1 text-xs font-medium ${
            row.status === 'active'
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200'
              : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
          }`}
        >
          {row.status}
        </span>
      )
    },
    { key: 'ip_address', label: 'IP' },
    {
      key: 'fingerprint',
      label: 'Fingerprint',
      render: (row) => (row.fingerprint ? `${row.fingerprint.slice(0, 12)}...` : '-')
    },
    {
      key: 'last_seen_at',
      label: 'Last Seen',
      render: (row) => (row.last_seen_at ? new Date(row.last_seen_at).toLocaleString() : '-')
    }
  ];

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Governance</h1>
        <p className="text-sm text-slate-500">Review queue, policy controls, and session monitoring.</p>
      </Card>
      <AdminDomainNav />
      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}
      <div className="grid gap-3 md:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <p className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</p>
            <p className="text-2xl font-semibold">{loading ? '...' : metric.value}</p>
          </Card>
        ))}
      </div>

      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Governance Policy</h2>
          <button type="button" className="btn-secondary" onClick={onSavePolicy} disabled={savingPolicy || loading}>
            {savingPolicy ? 'Saving...' : 'Save Policy'}
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700">
            <span className="text-sm">Two-person rule for destructive actions</span>
            <input
              type="checkbox"
              checked={Boolean(policy.two_person_rule_enabled)}
              onChange={(event) => setPolicy((prev) => ({ ...prev, two_person_rule_enabled: event.target.checked }))}
            />
          </label>
          <label className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700">
            <span className="text-sm">Role-change approval flow</span>
            <input
              type="checkbox"
              checked={Boolean(policy.role_change_approval_enabled)}
              onChange={(event) => setPolicy((prev) => ({ ...prev, role_change_approval_enabled: event.target.checked }))}
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Audit retention (days)</span>
            <input
              className="input"
              type="number"
              min={30}
              max={3650}
              value={policy.retention_days_audit ?? 365}
              onChange={(event) => setPolicy((prev) => ({ ...prev, retention_days_audit: event.target.value }))}
            />
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Session retention (days)</span>
            <input
              className="input"
              type="number"
              min={7}
              max={3650}
              value={policy.retention_days_sessions ?? 90}
              onChange={(event) => setPolicy((prev) => ({ ...prev, retention_days_sessions: event.target.value }))}
            />
          </label>
        </div>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Admin Action Review Queue</h2>
        <form className="grid gap-3 md:grid-cols-5" onSubmit={onCreateReview}>
          <label className="space-y-1 md:col-span-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Type</span>
            <select
              className="input"
              value={createReviewForm.review_type}
              onChange={(event) => setCreateReviewForm((prev) => ({ ...prev, review_type: event.target.value }))}
            >
              {reviewTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 md:col-span-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Action</span>
            <input
              className="input"
              required
              value={createReviewForm.action}
              onChange={(event) => setCreateReviewForm((prev) => ({ ...prev, action: event.target.value }))}
              placeholder="courses.delete"
            />
          </label>
          <label className="space-y-1 md:col-span-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Entity Type</span>
            <input
              className="input"
              required
              value={createReviewForm.entity_type}
              onChange={(event) => setCreateReviewForm((prev) => ({ ...prev, entity_type: event.target.value }))}
              placeholder="course"
            />
          </label>
          <label className="space-y-1 md:col-span-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Entity ID</span>
            <input
              className="input"
              value={createReviewForm.entity_id}
              onChange={(event) => setCreateReviewForm((prev) => ({ ...prev, entity_id: event.target.value }))}
              placeholder="Optional"
            />
          </label>
          <label className="space-y-1 md:col-span-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Reason</span>
            <input
              className="input"
              value={createReviewForm.reason}
              onChange={(event) => setCreateReviewForm((prev) => ({ ...prev, reason: event.target.value }))}
              placeholder="Why approval is needed"
            />
          </label>
          <div className="md:col-span-5">
            <button type="submit" className="btn-primary">
              Create Approval Request
            </button>
          </div>
        </form>
        <div className="flex items-center gap-2">
          <select
            className="input max-w-[220px]"
            value={reviewFilter}
            onChange={async (event) => {
              const next = event.target.value;
              setReviewFilter(next);
              await loadReviews(next);
            }}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="executed">Executed</option>
          </select>
          <button type="button" className="btn-secondary" onClick={() => loadReviews()} disabled={loadingReviews}>
            {loadingReviews ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        {reviews.length ? (
          <Table
            columns={reviewColumns}
            data={reviews}
            rowActions={[
              {
                key: 'approve',
                label: 'Approve',
                className: 'text-emerald-700 dark:text-emerald-300',
                onClick: (row) => onReviewDecision(row, true)
              },
              {
                key: 'reject',
                label: 'Reject',
                className: 'text-rose-700 dark:text-rose-300',
                onClick: (row) => onReviewDecision(row, false)
              }
            ]}
          />
        ) : (
          <EmptyState title="No review requests" description="Create a request to start two-person approval workflow." />
        )}
      </Card>

      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Device Session Monitor</h2>
          <div className="flex items-center gap-2">
            <select
              className="input max-w-[200px]"
              value={sessionFilter}
              onChange={async (event) => {
                const next = event.target.value;
                setSessionFilter(next);
                await loadSessions(next);
              }}
            >
              <option value="">All sessions</option>
              <option value="active">Active sessions</option>
              <option value="revoked">Revoked sessions</option>
            </select>
            <button type="button" className="btn-secondary" onClick={() => loadSessions()} disabled={loadingSessions}>
              {loadingSessions ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        {sessions.length ? (
          <Table columns={sessionColumns} data={sessions} />
        ) : (
          <EmptyState title="No sessions" description="Session tracker will show active and revoked device sessions here." />
        )}
      </Card>
    </div>
  );
}
