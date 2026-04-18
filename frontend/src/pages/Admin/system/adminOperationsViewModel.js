import {
  formatDateTime,
  formatDuration,
  formatMinutes,
  formatPercent,
  formatSeconds,
  formatUptime,
  pickBudgetStatus,
} from './adminSystemFormatters';

const HEALTH_STATUS_MAP = {
  healthy: { label: 'Healthy', variant: 'success' },
  ok: { label: 'Healthy', variant: 'success' },
  pass: { label: 'Healthy', variant: 'success' },
  up: { label: 'Healthy', variant: 'success' },
  degraded: { label: 'Warning', variant: 'warning' },
  warning: { label: 'Warning', variant: 'warning' },
  critical: { label: 'Critical', variant: 'danger' },
  unhealthy: { label: 'Critical', variant: 'danger' },
  down: { label: 'Critical', variant: 'danger' },
  error: { label: 'Critical', variant: 'danger' },
  failed: { label: 'Critical', variant: 'danger' },
};

const ALERT_VARIANT_MAP = {
  critical: 'danger',
  high: 'danger',
  warning: 'warning',
  medium: 'warning',
  info: 'default',
  low: 'default',
};

export function getHealthStatusMeta(status) {
  if (!status) {
    return { label: 'Unknown', variant: 'default' };
  }
  const normalized = String(status).trim().toLowerCase();
  return HEALTH_STATUS_MAP[normalized] || { label: String(status), variant: 'default' };
}

export function getAlertLevelMeta(level) {
  const normalized = String(level || 'info').trim().toLowerCase();
  return {
    label: normalized.toUpperCase(),
    variant: ALERT_VARIANT_MAP[normalized] || 'default',
  };
}

export function buildSystemOverviewModel({ data, aiMetrics, clubsMetrics, snapshotStore }) {
  const requestMetrics = data?.observability?.request_metrics || {};
  const schedulerMetrics = data?.observability?.scheduler_metrics || {};
  const collectionCounts = data?.collection_counts || {};
  const dbStatus = getHealthStatusMeta(data?.db_status);
  const retentionBoundStatus = snapshotStore?.is_within_retention_bound === false
    ? { label: 'Warning', variant: 'warning' }
    : { label: 'Healthy', variant: 'success' };

  return {
    healthCards: [
      {
        label: 'Database',
        value: dbStatus.label,
        tone: dbStatus.variant,
        detail: `Latest payload ${formatDateTime(data?.timestamp)}`,
      },
      {
        label: 'Uptime',
        value: formatUptime(data?.uptime_seconds),
        detail: 'Current service uptime window.',
      },
      {
        label: 'Errors (24h)',
        value: data?.error_count_24h ?? 0,
        detail: 'Application errors recorded in the last 24 hours.',
      },
      {
        label: 'Active Sessions (24h)',
        value: data?.active_sessions_24h ?? 0,
        detail: 'Authenticated activity recorded in the last 24 hours.',
      },
    ],
    trafficCards: [
      {
        label: 'Requests (15m)',
        value: requestMetrics.requests_15m ?? 0,
        detail: 'Rolling request volume.',
      },
      {
        label: '5xx Rate (15m)',
        value: formatPercent(requestMetrics.server_error_rate_pct_15m),
        detail: 'Server-side failure rate.',
      },
      {
        label: 'P95 Latency (15m)',
        value: formatDuration(requestMetrics.p95_duration_ms_15m),
        detail: 'Tail latency for recent traffic.',
      },
      {
        label: 'Slow Requests (15m)',
        value: requestMetrics.slow_requests_15m ?? 0,
        detail: 'Requests that crossed the slow threshold.',
      },
    ],
    clubsTrafficCards: [
      {
        label: 'Club Requests (15m)',
        value: clubsMetrics?.requests_15m ?? 0,
        detail: 'Traffic focused on club workspace paths.',
      },
      {
        label: 'Club P95 (15m)',
        value: formatDuration(clubsMetrics?.p95_duration_ms_15m),
        detail: 'Tail latency for club endpoints.',
      },
      {
        label: 'Club Slow (15m)',
        value: clubsMetrics?.slow_requests_15m ?? 0,
        detail: 'Slow club endpoint requests.',
      },
      {
        label: 'Club 5xx (15m)',
        value: clubsMetrics?.server_errors_15m ?? 0,
        detail: 'Server errors on club endpoints.',
      },
    ],
    capacityCards: [
      {
        label: 'AI Queue Depth',
        value: `${aiMetrics?.queued_jobs ?? 0} jobs`,
        status: pickBudgetStatus(aiMetrics?.queued_jobs, aiMetrics?.queue_warn_depth, aiMetrics?.queue_critical_depth),
        detail: `warn ${aiMetrics?.queue_warn_depth ?? '-'} | critical ${aiMetrics?.queue_critical_depth ?? '-'}`,
      },
      {
        label: 'Oldest Queued Age',
        value: formatSeconds(aiMetrics?.oldest_queued_age_seconds),
        status: pickBudgetStatus(
          aiMetrics?.oldest_queued_age_seconds,
          aiMetrics?.queue_warn_age_seconds,
          aiMetrics?.queue_critical_age_seconds
        ),
        detail: `warn ${formatSeconds(aiMetrics?.queue_warn_age_seconds)} | critical ${formatSeconds(aiMetrics?.queue_critical_age_seconds)}`,
      },
      {
        label: 'Fallback Rate',
        value: formatPercent(aiMetrics?.fallback_rate_pct_15m),
        status: pickBudgetStatus(
          aiMetrics?.fallback_rate_pct_15m,
          aiMetrics?.fallback_warning_rate_pct,
          aiMetrics?.fallback_critical_rate_pct
        ),
        detail: `warn ${formatPercent(aiMetrics?.fallback_warning_rate_pct)} | critical ${formatPercent(aiMetrics?.fallback_critical_rate_pct)}`,
      },
      {
        label: 'Similarity Candidates',
        value: aiMetrics?.last_similarity_candidate_count ?? 0,
        status: pickBudgetStatus(
          aiMetrics?.last_similarity_candidate_count,
          aiMetrics?.similarity_candidate_warn_threshold,
          aiMetrics?.similarity_candidate_cap
        ),
        detail: `warn ${aiMetrics?.similarity_candidate_warn_threshold ?? '-'} | cap ${aiMetrics?.similarity_candidate_cap ?? '-'}`,
      },
    ],
    schedulerCards: [
      {
        label: 'Scheduled Notices Pending',
        value: data?.scheduled_notice_dispatch?.pending_total ?? 0,
        detail: 'Notices waiting in the queue.',
      },
      {
        label: 'Scheduled Notices Due',
        value: data?.scheduled_notice_dispatch?.due_now_total ?? 0,
        detail: 'Notices due for immediate dispatch.',
      },
      {
        label: 'Retry Pending',
        value: data?.scheduled_notice_dispatch?.retry_pending_total ?? 0,
        detail: 'Scheduled notices queued for retry.',
      },
      {
        label: 'Oldest Dispatch Delay',
        value: formatSeconds(data?.scheduled_notice_dispatch?.oldest_due_age_seconds),
        detail: 'Age of the oldest due scheduled notice.',
      },
    ],
    storageCards: [
      {
        label: 'Snapshot Rows',
        value: snapshotStore?.retained_rows ?? 0,
        detail: 'Rows retained in the persisted snapshot store.',
      },
      {
        label: 'Retention Window',
        value: formatMinutes(snapshotStore?.retention_minutes),
        detail: 'Configured retention duration for snapshots.',
      },
      {
        label: 'Retention Bound',
        value: retentionBoundStatus.label,
        tone: retentionBoundStatus.variant,
        detail: 'Checks whether the store stayed within the retention guardrail.',
      },
      {
        label: 'Collections Tracked',
        value: Object.keys(collectionCounts).length,
        detail: 'Collections included in the latest counts payload.',
      },
    ],
    storageRows: [
      { label: 'Configured cap', value: snapshotStore?.max_retained_rows ?? '-' },
      { label: 'Last prune at', value: formatDateTime(snapshotStore?.last_pruned_at) },
      { label: 'Last prune bucket', value: snapshotStore?.last_pruned_bucket || '-' },
      { label: 'Last prune deleted', value: snapshotStore?.last_pruned_deleted_count ?? 0 },
    ],
    collectionRows: Object.entries(collectionCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((left, right) => left.name.localeCompare(right.name)),
    anomalyCards: [
      {
        label: 'Operational Alerts',
        value: data?.alert_count ?? 0,
        detail: 'Alerts active in the current health payload.',
      },
      {
        label: 'Slow Queries (24h)',
        value: data?.slow_query_count_24h ?? 0,
        detail: 'Slow-query incidents detected over the last 24 hours.',
      },
      {
        label: 'Scheduler Runs',
        value: schedulerMetrics?.runs_15m ?? 0,
        detail: 'Scheduler runs recorded in the last 15 minutes.',
      },
      {
        label: 'Scheduler Errors',
        value: schedulerMetrics?.errors_15m ?? 0,
        detail: 'Scheduler errors recorded in the last 15 minutes.',
      },
    ],
    hasRequestMetrics: Object.keys(requestMetrics).length > 0,
    hasAiMetrics: Object.keys(aiMetrics || {}).length > 0,
    hasCollectionRows: Object.keys(collectionCounts).length > 0,
  };
}

export function buildObservabilityDiagnosticsModel({
  data,
  historyData,
  persistedHistoryData,
  localHistoryData,
  localSnapshots,
  snapshotStore,
  usersAdminDashboard,
  usersAdminAlerts,
}) {
  const requestMetrics = data?.observability?.request_metrics || {};
  const clubsMetrics = data?.observability?.clubs_metrics || {};
  const schedulerMetrics = data?.observability?.scheduler_metrics || {};
  const topPaths = requestMetrics.top_paths_15m || [];
  const clubTopPaths = clubsMetrics.top_paths_15m || [];
  const usersLatency = usersAdminDashboard?.latency || {};
  const usersPagination = usersAdminDashboard?.pagination || {};
  const usersAlerts = Array.isArray(usersAdminAlerts) ? usersAdminAlerts : [];

  return {
    summaryCards: [
      {
        label: 'Latest Payload',
        value: formatDateTime(data?.timestamp),
        detail: 'Timestamp of the latest health payload.',
      },
      {
        label: 'Live Samples',
        value: historyData?.length ?? 0,
        detail: 'Short-term AI and queue samples available for charting.',
      },
      {
        label: 'Persisted Snapshots',
        value: persistedHistoryData?.length ?? 0,
        detail: 'Server-retained health snapshots.',
      },
      {
        label: 'Local Snapshots',
        value: localSnapshots?.length ?? 0,
        detail: 'Snapshots retained in this browser.',
      },
    ],
    endpointSummaryCards: [
      {
        label: 'Top Paths',
        value: topPaths.length,
        detail: 'Request paths with recent activity samples.',
      },
      {
        label: 'Club Paths',
        value: clubTopPaths.length,
        detail: 'Club-specific paths with recent traffic samples.',
      },
      {
        label: 'Requests (15m)',
        value: requestMetrics.requests_15m ?? 0,
        detail: 'Used as context for the path breakdown.',
      },
      {
        label: 'Club Requests (15m)',
        value: clubsMetrics.requests_15m ?? 0,
        detail: 'Recent traffic volume inside the clubs workspace.',
      },
    ],
    usersAdminCards: [
      {
        label: 'Users Requests (Window)',
        value: usersLatency.request_count ?? 0,
        detail: 'Requests sampled by users admin dashboard.',
      },
      {
        label: 'Users Error Rate',
        value: formatPercent(usersLatency.error_rate_pct),
        detail: 'Users admin list error-rate from dashboard source.',
      },
      {
        label: 'Users P95 Latency',
        value: formatDuration(usersLatency.p95_duration_ms),
        detail: 'Users admin list p95 latency.',
      },
      {
        label: 'Users Empty Page Rate',
        value: formatPercent(usersPagination.empty_page_rate_pct),
        detail: 'Pagination quality signal for users list.',
      },
    ],
    usersAdminAlertRows: usersAlerts.map((alert) => ({
      code: alert.code || '-',
      level: String(alert.level || 'warning').toUpperCase(),
      message: alert.message || '',
      threshold:
        alert.threshold_value !== undefined && alert.current_value !== undefined
          ? `${alert.current_value} ${alert.comparison || '>'} ${alert.threshold_value}`
          : '-',
    })),
    snapshotCards: [
      {
        label: 'Retained Rows',
        value: snapshotStore?.retained_rows ?? 0,
        detail: 'Persisted rows currently retained.',
      },
      {
        label: 'Snapshot Cap',
        value: snapshotStore?.max_retained_rows ?? '-',
        detail: 'Configured retention cap for the snapshot store.',
      },
      {
        label: 'Last Prune Deleted',
        value: snapshotStore?.last_pruned_deleted_count ?? 0,
        detail: 'Rows deleted by the latest prune cycle.',
      },
      {
        label: 'Retention Bound',
        value: snapshotStore?.is_within_retention_bound === false ? 'Warning' : 'Healthy',
        tone: snapshotStore?.is_within_retention_bound === false ? 'warning' : 'success',
        detail: 'Signals whether retention stayed within its configured bound.',
      },
    ],
    schedulerRows: [
      { label: 'Scheduler status', value: data?.scheduler?.status || '-' },
      { label: 'Scheduler last heartbeat', value: formatDateTime(data?.scheduler?.last_heartbeat_at) },
      { label: 'Scheduler lock owner', value: data?.scheduler_lock?.owner || '-' },
      { label: 'Scheduler lock expires', value: formatDateTime(data?.scheduler_lock?.expires_at) },
      { label: 'Scheduler runs (15m)', value: schedulerMetrics?.runs_15m ?? 0 },
      { label: 'Scheduler errors (15m)', value: schedulerMetrics?.errors_15m ?? 0 },
      { label: 'Pending scheduled notices', value: data?.scheduled_notice_dispatch?.pending_total ?? 0 },
      { label: 'Oldest due notice', value: formatSeconds(data?.scheduled_notice_dispatch?.oldest_due_age_seconds) },
    ],
    topPaths,
    clubTopPaths,
    hasTopPaths: topPaths.length > 0,
    hasClubTopPaths: clubTopPaths.length > 0,
    hasUsersAdminAlerts: usersAlerts.length > 0,
  };
}
