import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import InlineErrorState from '../../components/ui/InlineErrorState';
import PageLoader from '../../components/ui/PageLoader';
import Table from '../../components/ui/Table';
import EmptyState from '../../components/ui/EmptyState';
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
import { buildGovernanceResultLinks, buildGovernanceReviewFollowUp, buildGovernanceSessionFollowUp, buildRbacPath } from './adminWorkflowLinks';

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
  const [reviewError, setReviewError] = useState('');
  const [sessions, setSessions] = useState([]);
  const [sessionFilter, setSessionFilter] = useState('active');
  const [sessionError, setSessionError] = useState('');
  const [createReviewForm, setCreateReviewForm] = useState({
    review_type: 'destructive',
    action: '',
    entity_type: '',
    entity_id: '',
    reason: ''
  });
  const [lastOutcome, setLastOutcome] = useState(null);

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
    void loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    setError('');
    setReviewError('');
    setSessionError('');
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
    setReviewError('');
    try {
      const rows = await fetchGovernanceReviews({ status: status || undefined, limit: 100 });
      setReviews(rows);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load reviews');
      setReviewError(message);
      pushToast({ title: 'Reviews load failed', description: message, variant: 'error' });
    } finally {
      setLoadingReviews(false);
    }
  }

  async function loadSessions(status = sessionFilter) {
    setLoadingSessions(true);
    setSessionError('');
    try {
      const rows = await fetchGovernanceSessions({ status: status || undefined, limit: 50 });
      setSessions(rows.items || []);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load sessions');
      setSessionError(message);
      pushToast({ title: 'Sessions load failed', description: message, variant: 'error' });
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
      setLastOutcome({
        title: 'Policy saved',
        description: 'Open Audit Logs to verify the policy mutation trail or RBAC to continue access-control follow-up.',
        ...buildGovernanceResultLinks({
          action: 'update',
          entityType: 'governance_policy',
          resourceType: 'governance_policy',
        }),
      });
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
      pushToast({
        title: approve ? 'Review approved' : 'Review rejected',
        description: `Review ${row.public_id || row.id} updated.`,
        variant: 'success'
      });
      setLastOutcome({
        title: approve ? 'Review approved' : 'Review rejected',
        description: 'Continue with RBAC for role-related follow-up or use Audit Logs to verify the decision trail.',
        ...buildGovernanceResultLinks({
          reviewType: row.review_type,
          action: row.action,
          entityType: row.entity_type,
          resourceType: row.entity_type,
        }),
      });
      await Promise.all([loadReviews(), reloadDashboard()]);
    } catch (err) {
      pushToast({ title: 'Decision failed', description: formatApiError(err, 'Failed to update review'), variant: 'error' });
    }
  }

  const reviewColumns = [
    { key: 'public_id', label: 'Short ID', priority: 'high', render: (row) => row.public_id || row.id || '-' },
    { key: 'review_type', label: 'Type', priority: 'medium' },
    { key: 'action', label: 'Action', priority: 'high' },
    { key: 'entity_label', label: 'Entity', priority: 'high', render: (row) => row.entity_label || row.entity_type || '-' },
    { key: 'status', label: 'Status', priority: 'high' },
    { key: 'requested_by_label', label: 'Requested By', priority: 'low', render: (row) => row.requested_by_label || row.requested_by || '-' },
    {
      key: 'created_at',
      priority: 'medium',
      label: 'Created',
      render: (row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-')
    },
    {
      key: 'follow_up',
      priority: 'medium',
      label: 'Follow-up',
      render: (row) => {
        const followUp = buildGovernanceReviewFollowUp(row);
        return (
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary !px-3 !py-1.5 text-xs" to={followUp.primaryTo}>
              {followUp.primaryLabel}
            </Link>
            <Link className="btn-secondary !px-3 !py-1.5 text-xs" to={followUp.secondaryTo}>
              {followUp.secondaryLabel}
            </Link>
          </div>
        );
      }
    }
  ];

  const sessionColumns = [
    { key: 'user_label', label: 'User', priority: 'high', render: (row) => row.user_label || row.user_name || row.user_email || row.user_id || '-' },
    {
      key: 'status',
      priority: 'high',
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
    { key: 'ip_address', label: 'IP', priority: 'medium' },
    {
      key: 'fingerprint',
      priority: 'low',
      label: 'Fingerprint',
      render: (row) => (row.fingerprint ? `${row.fingerprint.slice(0, 12)}...` : '-')
    },
    {
      key: 'last_seen_at',
      priority: 'medium',
      label: 'Last Seen',
      render: (row) => (row.last_seen_at ? new Date(row.last_seen_at).toLocaleString() : '-')
    },
    {
      key: 'follow_up',
      priority: 'medium',
      label: 'Follow-up',
      render: (row) => {
        const followUp = buildGovernanceSessionFollowUp(row);
        return (
          <Link className="btn-secondary !px-3 !py-1.5 text-xs" to={followUp.primaryTo}>
            {followUp.primaryLabel}
          </Link>
        );
      }
    }
  ];
  const initialLoading = loading && !dashboard && reviews.length === 0 && sessions.length === 0;

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Governance</h1>
        <p className="text-sm text-slate-500">Review queue, policy controls, and session monitoring.</p>
      </Card>
      {error ? (
        <InlineErrorState
          title="Governance unavailable"
          description={error}
          onRetry={() => void loadAll()}
        />
      ) : null}
      {initialLoading ? <PageLoader compact label="Loading governance workspace..." /> : null}
      <div className="grid gap-3 md:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <p className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</p>
            <p className="text-2xl font-semibold">{loading ? '...' : metric.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Card className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold">Related Actions</h2>
            <p className="text-sm text-slate-500">
              Governance decisions usually need an access-control follow-up in RBAC or a final verification pass in Audit Logs.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" to={buildRbacPath({ context: 'governance_follow_up' })}>Open RBAC</Link>
            <Link className="btn-secondary" to="/audit-logs">Open Audit Logs</Link>
          </div>
        </Card>

        {lastOutcome ? (
          <Card className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">{lastOutcome.title}</h2>
              <p className="text-sm text-slate-500">{lastOutcome.description}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link className="btn-secondary" to={lastOutcome.auditTo}>Open Audit Logs</Link>
              <Link className="btn-secondary" to={lastOutcome.rbacTo}>Open RBAC</Link>
            </div>
          </Card>
        ) : null}
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
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Admin Action Review Queue</h2>
          <p className="text-sm text-slate-500">Approve here, then use the follow-up links to jump straight into the access or audit surface that closes the loop.</p>
        </div>
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
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Entity ID / Ref</span>
            <input
              className="input"
              value={createReviewForm.entity_id}
              onChange={(event) => setCreateReviewForm((prev) => ({ ...prev, entity_id: event.target.value }))}
              placeholder="Optional internal or public ID"
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
        {loadingReviews && !reviews.length ? (
          <PageLoader compact label="Loading review queue..." />
        ) : reviewError ? (
          <InlineErrorState compact title="Review queue unavailable" description={reviewError} onRetry={() => void loadReviews()} />
        ) : reviews.length ? (
          <Table
            columns={reviewColumns}
            data={reviews}
            responsive
            mobileBreakpoint="md"
            stickyActions
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
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">Device Session Monitor</h2>
            <p className="text-sm text-slate-500">Use session follow-up links to verify suspicious activity in Audit Logs without rebuilding the filter set.</p>
          </div>
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
        {loadingSessions && !sessions.length ? (
          <PageLoader compact label="Loading device sessions..." />
        ) : sessionError ? (
          <InlineErrorState compact title="Session monitor unavailable" description={sessionError} onRetry={() => void loadSessions()} />
        ) : sessions.length ? (
          <Table columns={sessionColumns} data={sessions} responsive mobileBreakpoint="md" stickyActions />
        ) : (
          <EmptyState title="No sessions" description="Session tracker will show active and revoked device sessions here." />
        )}
      </Card>
    </div>
  );
}
