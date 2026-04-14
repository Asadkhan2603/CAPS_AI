import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import InlineErrorState from '../../components/ui/InlineErrorState';
import Skeleton from '../../components/ui/Skeleton';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../services/apiClient';
import {
  fetchGovernanceDashboard,
  fetchGovernanceReviews,
} from '../../services/adminGovernanceApi';
import { formatApiError } from '../../utils/apiError';
import {
  getAdminDashboardAccess,
  getAdminDashboardCriticalCards,
  getAdminDashboardQuickActions,
} from './adminDashboardConfig';
import {
  mapAcademicAdminDashboardClosure,
  mapDashboardActivityItems,
  mapDashboardOutcomeItems,
} from './adminDashboardActivity';

const panelToneClasses = {
  default: 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900',
  success: 'border-emerald-200 bg-emerald-50 dark:border-emerald-900/40 dark:bg-emerald-950/20',
  warning: 'border-amber-200 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-950/20',
  danger: 'border-rose-200 bg-rose-50 dark:border-rose-900/40 dark:bg-rose-950/20',
  info: 'border-brand-200 bg-brand-50 dark:border-brand-900/40 dark:bg-brand-950/20',
};

const panelTextClasses = {
  default: 'text-slate-700 dark:text-slate-200',
  success: 'text-emerald-800 dark:text-emerald-200',
  warning: 'text-amber-800 dark:text-amber-200',
  danger: 'text-rose-800 dark:text-rose-200',
  info: 'text-brand-800 dark:text-brand-200',
};

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const adminType = user?.admin_type || 'admin';
  const access = useMemo(() => getAdminDashboardAccess(adminType), [adminType]);
  const quickActions = useMemo(() => getAdminDashboardQuickActions(adminType), [adminType]);
  const [summary, setSummary] = useState({});
  const [system, setSystem] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [pendingReviews, setPendingReviews] = useState([]);
  const [error, setError] = useState('');
  const [loadIssues, setLoadIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [closureLoading, setClosureLoading] = useState(true);
  const [closureError, setClosureError] = useState('');
  const [auditActivityRows, setAuditActivityRows] = useState([]);
  const [onboardingOverview, setOnboardingOverview] = useState(null);
  const [closureReloadToken, setClosureReloadToken] = useState(0);

  const criticalCards = useMemo(
    () => getAdminDashboardCriticalCards({ summary, system, governance, access }),
    [access, governance, summary, system]
  );
  const closureContent = useMemo(
    () => mapAcademicAdminDashboardClosure(onboardingOverview),
    [onboardingOverview]
  );
  const recentActivityItems = useMemo(
    () => mapDashboardActivityItems(auditActivityRows),
    [auditActivityRows]
  );
  const actionOutcomeItems = useMemo(
    () => mapDashboardOutcomeItems(auditActivityRows),
    [auditActivityRows]
  );

  useEffect(() => {
    let alive = true;

    async function loadDashboard() {
      setLoading(true);
      setError('');
      setLoadIssues([]);

      const [analyticsResult, systemResult, governanceResult, reviewsResult] =
        await Promise.allSettled([
          apiClient.get('/admin/analytics/bootstrap'),
          access.canSystem ? apiClient.get('/admin/system/health') : Promise.resolve(null),
          access.canGovernance ? fetchGovernanceDashboard() : Promise.resolve(null),
          access.canGovernance
            ? fetchGovernanceReviews({ status: 'pending', limit: 3 })
            : Promise.resolve([]),
        ]);

      if (!alive) {
        return;
      }

      const nextIssues = [];

      if (analyticsResult.status === 'fulfilled') {
        setSummary(analyticsResult.value?.data?.overview || {});
      } else {
        setSummary({});
        nextIssues.push('platform overview');
      }

      if (access.canSystem) {
        if (systemResult.status === 'fulfilled') {
          setSystem(systemResult.value?.data || null);
        } else {
          setSystem(null);
          nextIssues.push('system health');
        }
      } else {
        setSystem(null);
      }

      if (access.canGovernance) {
        if (governanceResult.status === 'fulfilled') {
          setGovernance(governanceResult.value || null);
        } else {
          setGovernance(null);
          nextIssues.push('governance summary');
        }

        if (reviewsResult.status === 'fulfilled') {
          setPendingReviews(Array.isArray(reviewsResult.value) ? reviewsResult.value : []);
        } else {
          setPendingReviews([]);
          nextIssues.push('approval queue');
        }
      } else {
        setGovernance(null);
        setPendingReviews([]);
      }

      setLoadIssues(nextIssues);

      if (nextIssues.length === 4 || (!access.canGovernance && !access.canSystem && nextIssues.length === 1)) {
        const primaryError =
          analyticsResult.status === 'rejected'
            ? analyticsResult.reason
            : systemResult.status === 'rejected'
              ? systemResult.reason
              : governanceResult.status === 'rejected'
                ? governanceResult.reason
                : reviewsResult.status === 'rejected'
                  ? reviewsResult.reason
                  : null;
        setError(formatApiError(primaryError, 'Failed to load admin dashboard'));
      }

      setLoading(false);
    }

    void loadDashboard();

    return () => {
      alive = false;
    };
  }, [access.canGovernance, access.canSystem]);

  useEffect(() => {
    let alive = true;

    async function loadClosureBand() {
      setClosureLoading(true);
      setClosureError('');

      try {
        if (access.canAuditLogs) {
          const response = await apiClient.get('/audit-logs/', { params: { limit: 5 } });
          if (!alive) {
            return;
          }
          setAuditActivityRows(Array.isArray(response.data) ? response.data : []);
          setOnboardingOverview(null);
        } else if (access.canOnboarding) {
          const response = await apiClient.get('/admin/analytics/overview');
          if (!alive) {
            return;
          }
          setOnboardingOverview(response.data || null);
          setAuditActivityRows([]);
        } else {
          setAuditActivityRows([]);
          setOnboardingOverview(null);
        }
      } catch (err) {
        if (!alive) {
          return;
        }
        setAuditActivityRows([]);
        setOnboardingOverview(null);
        setClosureError(
          formatApiError(
            err,
            access.canAuditLogs
              ? 'Failed to load recent admin activity'
              : 'Failed to load onboarding progress snapshot'
          )
        );
      } finally {
        if (alive) {
          setClosureLoading(false);
        }
      }
    }

    void loadClosureBand();

    return () => {
      alive = false;
    };
  }, [access.canAuditLogs, access.canOnboarding, closureReloadToken]);

  return (
    <div className="space-y-5 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold">Admin Control Center</h1>
              <Badge variant="info">{adminType.replaceAll('_', ' ')}</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Prioritized admin workspace for approvals, alerts, and role-aware operational actions.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>Navigation lives in the sidebar and quick search.</span>
            {loadIssues.length ? <Badge variant="warning">Partial live data</Badge> : null}
          </div>
        </div>

        {loadIssues.length && !error ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
            Some live dashboard data is unavailable: {loadIssues.join(', ')}.
          </div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200">
            {error}
          </div>
        ) : null}
      </Card>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Quick Actions</h2>
          <p className="text-xs text-slate-500">Most-used actions for your current admin scope.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {quickActions.map((action) => (
            <Link
              key={action.to}
              to={action.to}
              className="rounded-[1.4rem] border border-slate-200 bg-white p-4 shadow-[0_16px_40px_-34px_rgba(15,23,42,0.34)] transition hover:border-brand-200 hover:bg-brand-50/40 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-900/40 dark:hover:bg-brand-950/20"
            >
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{action.label}</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{action.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Critical Status</h2>
          <p className="text-xs text-slate-500">Four high-signal indicators for the current admin role.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {loading
            ? Array.from({ length: 4 }).map((_, index) => (
                <Card key={`critical-skeleton-${index}`} className="space-y-3">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-9 w-24" />
                  <Skeleton className="h-4 w-40" />
                </Card>
              ))
            : criticalCards.map((card) => (
                <StatusCard key={card.key} {...card} />
              ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Recent Workflow Closure</h2>
          <p className="text-xs text-slate-500">
            Recent admin verification and proof-of-completion signals.
          </p>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Recent Activity</h2>
                <p className="text-sm text-slate-500">
                  {access.canAuditLogs
                    ? 'Latest logged admin actions with direct audit verification.'
                    : 'Current onboarding progress and the next academic setup step.'}
                </p>
              </div>
              <Link className="btn-secondary" to={access.canAuditLogs ? '/audit-logs' : '/admin/onboarding'}>
                {access.canAuditLogs ? 'Open Audit Logs' : 'Open Onboarding'}
              </Link>
            </div>

            {closureLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : null}

            {!closureLoading && closureError ? (
              <InlineErrorState
                compact
                title={access.canAuditLogs ? 'Recent activity unavailable' : 'Onboarding progress unavailable'}
                description={closureError}
                onRetry={() => setClosureReloadToken((value) => value + 1)}
              />
            ) : null}

            {!closureLoading && !closureError && access.canAuditLogs ? (
              recentActivityItems.length ? (
                <div className="space-y-3">
                  {recentActivityItems.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {item.actionLabel}
                        </p>
                        <span className="text-xs text-slate-500">{item.timestampLabel}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{item.entityLabel}</p>
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs text-slate-500">Actor: {item.actorLabel}</p>
                        <Link className="btn-secondary !px-3 !py-1.5 text-xs" to={item.to}>
                          View in Audit Logs
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  compact
                  title="No recent admin activity yet"
                  description="Audit-backed admin actions will appear here once a new approval, restore, access update, or session event is logged."
                />
              )
            ) : null}

            {!closureLoading && !closureError && !access.canAuditLogs ? (
              closureContent.activity ? (
                <div className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <CompactMetric
                      label="Progress"
                      value={`${closureContent.activity.progressPercent}%`}
                    />
                    <CompactMetric
                      label="Steps Complete"
                      value={`${closureContent.activity.completedSteps}/${closureContent.activity.totalSteps}`}
                    />
                    <CompactMetric
                      label="Next Step"
                      value={closureContent.activity.nextStepLabel}
                    />
                  </div>
                  <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {closureContent.activity.nextStepLabel}
                    </p>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {closureContent.activity.nextStepDescription}
                    </p>
                    <Link className="btn-secondary mt-3 w-fit" to={closureContent.activity.ctaTo}>
                      {closureContent.activity.ctaLabel}
                    </Link>
                  </div>
                </div>
              ) : (
                <EmptyState
                  compact
                  title="No onboarding progress snapshot yet"
                  description="Progress and next-step guidance will appear here once the academic setup flow has recorded activity."
                  action={
                    <Link className="btn-secondary" to="/admin/onboarding">
                      Open Onboarding
                    </Link>
                  }
                />
              )
            ) : null}
          </Card>

          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Action Outcomes</h2>
                <p className="text-sm text-slate-500">
                  {access.canAuditLogs
                    ? 'Recent proof-of-completion signals grouped from the audit trail.'
                    : 'Latest onboarding milestone plus the next step needed to keep setup moving.'}
                </p>
              </div>
              <Link
                className="btn-secondary"
                to={access.canAuditLogs ? '/audit-logs' : closureContent.outcomes?.ctaTo || '/admin/onboarding'}
              >
                {access.canAuditLogs ? 'Review Outcomes' : closureContent.outcomes?.ctaLabel || 'Open Onboarding'}
              </Link>
            </div>

            {closureLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : null}

            {!closureLoading && closureError ? (
              <InlineErrorState
                compact
                title={access.canAuditLogs ? 'Action outcomes unavailable' : 'Onboarding outcomes unavailable'}
                description={closureError}
                onRetry={() => setClosureReloadToken((value) => value + 1)}
              />
            ) : null}

            {!closureLoading && !closureError && access.canAuditLogs ? (
              actionOutcomeItems.length ? (
                <div className="space-y-3">
                  {actionOutcomeItems.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {item.title}
                        </p>
                        <span className="text-xs text-slate-500">{item.timestampLabel}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{item.detail}</p>
                      <Link className="btn-secondary mt-3 w-fit !px-3 !py-1.5 text-xs" to={item.to}>
                        Open matching audit trail
                      </Link>
                    </div>
                  ))}
                  {actionOutcomeItems.length < 3 ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      More outcomes will appear after the next admin action.
                    </div>
                  ) : null}
                </div>
              ) : (
                <EmptyState
                  compact
                  title="No action outcomes yet"
                  description="Proof-of-completion outcomes will appear here after the next restore, access update, governance decision, or session event."
                />
              )
            ) : null}

            {!closureLoading && !closureError && !access.canAuditLogs ? (
              closureContent.outcomes ? (
                <div className="space-y-3">
                  <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                      Latest completed milestone
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {closureContent.outcomes.latestCompletedLabel}
                    </p>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {closureContent.outcomes.latestCompletedDescription}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                      Next recommended step
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {closureContent.outcomes.nextStepLabel}
                    </p>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {closureContent.outcomes.nextStepDescription}
                    </p>
                    <Link className="btn-secondary mt-3 w-fit" to={closureContent.outcomes.ctaTo}>
                      {closureContent.outcomes.ctaLabel}
                    </Link>
                  </div>
                </div>
              ) : (
                <EmptyState
                  compact
                  title="No onboarding outcomes yet"
                  description="Completed milestones and the next recommended academic setup action will appear here after onboarding progress begins."
                  action={
                    <Link className="btn-secondary" to="/admin/onboarding">
                      Open Onboarding
                    </Link>
                  }
                />
              )
            ) : null}
          </Card>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        {access.canGovernance ? (
          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Pending Approval Queue</h2>
                <p className="text-sm text-slate-500">Latest governance requests that still need action.</p>
              </div>
              <Link className="btn-secondary" to="/admin/governance">
                Open Governance
              </Link>
            </div>
            {loading && !pendingReviews.length ? (
              <div className="space-y-2">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : pendingReviews.length ? (
              <div className="space-y-3">
                {pendingReviews.map((row) => (
                  <div
                    key={row.id}
                    className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {row.public_id || row.id}
                      </p>
                      <Badge variant="warning">{row.status || 'pending'}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                      {row.action || 'Unknown action'} on {row.entity_label || row.entity_type || 'entity'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Requested by {row.requested_by_label || row.requested_by || 'unknown'} |{' '}
                      {row.created_at ? new Date(row.created_at).toLocaleString() : '-'}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No pending approvals"
                description="Governance requests waiting for approval will appear here."
              />
            )}
          </Card>
        ) : null}

        {access.canSystem ? (
          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Operational Alerts</h2>
                <p className="text-sm text-slate-500">Active alerts pulled from the system health surface.</p>
              </div>
              <Link className="btn-secondary" to="/admin/system">
                Open System Health
              </Link>
            </div>
            {loading && !system ? (
              <div className="space-y-2">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : system?.alerts?.length ? (
              <div className="space-y-3">
                {system.alerts.slice(0, 3).map((alert) => (
                  <div
                    key={alert.code}
                    className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold">{alert.code}</p>
                      <Badge variant={alert.level === 'critical' ? 'danger' : 'warning'}>
                        {alert.level || 'warning'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm">{alert.message}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No active operational alerts"
                description="Current system alerts will surface here when the platform needs attention."
              />
            )}
          </Card>
        ) : null}

        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Platform Overview</h2>
              <p className="text-sm text-slate-500">Current high-level platform counts from admin analytics.</p>
            </div>
            <Link className="btn-secondary" to="/admin/analytics">
              Open Analytics
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <OverviewMetric label="Users" value={summary.total_users} />
            <OverviewMetric label="Students" value={summary.active_students} />
            <OverviewMetric label="Assignments" value={summary.assignments_total} />
            <OverviewMetric label="Clubs" value={summary.active_clubs} />
          </div>
        </Card>

        <Card className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">System Posture</h2>
            <p className="text-sm text-slate-500">
              Combined status snapshot for system health and governance posture.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <PostureItem
              label="Database"
              value={access.canSystem ? system?.db_status || '-' : 'Not available'}
              description={
                access.canSystem
                  ? 'Primary data store health from the system surface.'
                  : 'Your admin scope does not include system diagnostics.'
              }
            />
            <PostureItem
              label="Governance policy"
              value={
                access.canGovernance
                  ? governance?.policy?.two_person_rule_enabled
                    ? 'Two-person rule on'
                    : 'Two-person rule off'
                  : 'Not available'
              }
              description={
                access.canGovernance
                  ? `Role-change approval ${
                      governance?.policy?.role_change_approval_enabled ? 'enabled' : 'disabled'
                    }.`
                  : 'Your admin scope does not include governance policy controls.'
              }
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <PostureItem
              label="Snapshot"
              value={summary.total_users !== undefined ? 'Analytics loaded' : 'Waiting on analytics'}
              description="Dashboard keeps rendering with partial live data even if one source fails."
            />
            <PostureItem
              label="Recommended next step"
              value={quickActions[0]?.label || 'Review dashboard'}
              description="Next action is derived from the current admin role."
            />
          </div>
        </Card>
      </div>
    </div>
  );
}

function StatusCard({ label, value, helper, variant = 'default' }) {
  return (
    <Card className={`space-y-2 border ${panelToneClasses[variant] || panelToneClasses.default}`}>
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{label}</p>
      <p className={`text-3xl font-semibold ${panelTextClasses[variant] || panelTextClasses.default}`}>
        {value ?? 0}
      </p>
      <p className="text-sm text-slate-600 dark:text-slate-300">{helper}</p>
    </Card>
  );
}

function OverviewMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800">
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value ?? 0}</p>
    </div>
  );
}

function PostureItem({ label, value, description }) {
  return (
    <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800">
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  );
}

function CompactMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-800">
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  );
}
