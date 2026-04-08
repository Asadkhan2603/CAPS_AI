import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { useToast } from '../../hooks/useToast';
import AlertRoutingHistorySection from './system/AlertRoutingHistorySection';
import ClubObservabilityTrendSection from './system/ClubObservabilityTrendSection';
import SystemHealthHistoryCharts from './system/SystemHealthHistoryCharts';
import { AUTO_REFRESH_MS, useAdminSystemHealth } from './system/useAdminSystemHealth';
import {
  formatDateTime,
  formatDuration,
  formatMinutes,
  formatPercent,
  formatSeconds,
  formatUptime,
  pickBudgetStatus,
  statusClasses,
} from './system/adminSystemFormatters';

export default function AdminSystemPage() {
  const { pushToast } = useToast();
  const {
    aiMetrics,
    alertRouteHistory,
    alertRouting,
    clubsObservability,
    clubsMetrics,
    clearSnapshots,
    data,
    error,
    exportSnapshots,
    historyData,
    isAutoRefresh,
    isRefreshing,
    loadHealth,
    localHistoryData,
    localSnapshots,
    persistedHistoryData,
    setIsAutoRefresh,
    snapshotStore,
  } = useAdminSystemHealth({ pushToast });

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">System Health</h1>
            <p className="text-sm text-slate-500">Runtime health, DB status, and key collection counts.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void loadHealth({ silent: false, forceRefresh: true })}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
            </button>
            <button
              type="button"
              onClick={() => setIsAutoRefresh((value) => !value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Auto Refresh: {isAutoRefresh ? 'On' : 'Off'}
            </button>
            <button
              type="button"
              onClick={() => void exportSnapshots()}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={clearSnapshots}
              className="rounded-lg border border-rose-300 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-950/40"
            >
              Clear Local History
            </button>
          </div>
        </div>
        <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-4">
          <div>Auto refresh cadence: {AUTO_REFRESH_MS / 1000}s</div>
          <div>Persisted snapshots shown: {data?.snapshot_history?.length ?? 0}</div>
          <div>Stored local snapshots: {localSnapshots.length}</div>
          <div>Latest payload: {formatDateTime(data?.timestamp)}</div>
        </div>
      </Card>
      <AdminDomainNav />
      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="DB Status" value={data?.db_status || '-'} />
        <Metric label="Uptime" value={formatUptime(data?.uptime_seconds)} />
        <Metric label="Errors (24h)" value={data?.error_count_24h ?? 0} />
        <Metric label="Active Sessions (24h)" value={data?.active_sessions_24h ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="Slow Queries (24h)" value={data?.slow_query_count_24h ?? 0} />
        <Metric label="Operational Alerts" value={data?.alert_count ?? 0} />
        <Metric label="Timestamp" value={data?.timestamp ? new Date(data.timestamp).toLocaleString() : '-'} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Persisted Snapshot Rows" value={snapshotStore.retained_rows ?? 0} />
        <Metric label="Snapshot Retention Window" value={formatMinutes(snapshotStore.retention_minutes)} />
        <Metric label="Snapshot Store Bound" value={snapshotStore.is_within_retention_bound === false ? 'Drifted' : 'Within Bound'} />
        <Metric label="Last Prune Deleted" value={snapshotStore.last_pruned_deleted_count ?? 0} />
      </div>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Snapshot Store Status</p>
        <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-2 xl:grid-cols-4">
          <div>Retained rows: {snapshotStore.retained_rows ?? 0}</div>
          <div>Configured cap: {snapshotStore.max_retained_rows ?? '-'}</div>
          <div>Last prune at: {formatDateTime(snapshotStore.last_pruned_at)}</div>
          <div>Last prune bucket: {snapshotStore.last_pruned_bucket || '-'}</div>
        </div>
      </Card>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Operational Alerts</p>
        {data?.alerts?.length ? (
          <div className="space-y-2">
            {data.alerts.map((alert) => (
              <div
                key={alert.code}
                className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100"
              >
                <div className="font-medium">
                  {alert.level?.toUpperCase() || 'INFO'} | {alert.code}
                </div>
                <div>{alert.message}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-emerald-600 dark:text-emerald-400">No active operational alerts.</p>
        )}
      </Card>
      <AlertRoutingHistorySection alertRouting={alertRouting} alertRouteHistory={alertRouteHistory} />
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Requests (15m)" value={data?.observability?.request_metrics?.requests_15m ?? 0} />
        <Metric label="5xx Rate (15m)" value={formatPercent(data?.observability?.request_metrics?.server_error_rate_pct_15m)} />
        <Metric label="P95 (15m)" value={formatDuration(data?.observability?.request_metrics?.p95_duration_ms_15m)} />
        <Metric label="Slow Requests (15m)" value={data?.observability?.request_metrics?.slow_requests_15m ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Club Requests (15m)" value={clubsMetrics.requests_15m ?? 0} />
        <Metric label="Club P95 (15m)" value={formatDuration(clubsMetrics.p95_duration_ms_15m)} />
        <Metric label="Club Slow (15m)" value={clubsMetrics.slow_requests_15m ?? 0} />
        <Metric label="Club 5xx (15m)" value={clubsMetrics.server_errors_15m ?? 0} />
      </div>
      <ClubObservabilityTrendSection clubsObservability={clubsObservability} />
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="AI Queued Jobs" value={aiMetrics.queued_jobs ?? 0} />
        <Metric label="Oldest AI Job Age" value={formatSeconds(aiMetrics.oldest_queued_age_seconds)} />
        <Metric label="AI Fallback Rate (15m)" value={formatPercent(aiMetrics.fallback_rate_pct_15m)} />
        <Metric label="Similarity Candidates" value={aiMetrics.last_similarity_candidate_count ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Scheduled Notices Pending" value={data?.scheduled_notice_dispatch?.pending_total ?? 0} />
        <Metric label="Scheduled Notices Due" value={data?.scheduled_notice_dispatch?.due_now_total ?? 0} />
        <Metric label="Scheduled Notice Retries" value={data?.scheduled_notice_dispatch?.retry_pending_total ?? 0} />
        <Metric label="Oldest Scheduled Delay" value={formatSeconds(data?.scheduled_notice_dispatch?.oldest_due_age_seconds)} />
      </div>
      <Card className="space-y-3">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">AI Capacity Status</p>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <CapacityStatus
            label="Queue Depth"
            value={`${aiMetrics.queued_jobs ?? 0} jobs`}
            status={pickBudgetStatus(aiMetrics.queued_jobs, aiMetrics.queue_warn_depth, aiMetrics.queue_critical_depth)}
            detail={`warn ${aiMetrics.queue_warn_depth ?? '-'} | critical ${aiMetrics.queue_critical_depth ?? '-'}`}
          />
          <CapacityStatus
            label="Oldest Queued Age"
            value={formatSeconds(aiMetrics.oldest_queued_age_seconds)}
            status={pickBudgetStatus(aiMetrics.oldest_queued_age_seconds, aiMetrics.queue_warn_age_seconds, aiMetrics.queue_critical_age_seconds)}
            detail={`warn ${formatSeconds(aiMetrics.queue_warn_age_seconds)} | critical ${formatSeconds(aiMetrics.queue_critical_age_seconds)}`}
          />
          <CapacityStatus
            label="Fallback Rate"
            value={formatPercent(aiMetrics.fallback_rate_pct_15m)}
            status={pickBudgetStatus(aiMetrics.fallback_rate_pct_15m, aiMetrics.fallback_warning_rate_pct, aiMetrics.fallback_critical_rate_pct)}
            detail={`warn ${formatPercent(aiMetrics.fallback_warning_rate_pct)} | critical ${formatPercent(aiMetrics.fallback_critical_rate_pct)}`}
          />
          <CapacityStatus
            label="Similarity Candidates"
            value={aiMetrics.last_similarity_candidate_count ?? 0}
            status={pickBudgetStatus(aiMetrics.last_similarity_candidate_count, aiMetrics.similarity_candidate_warn_threshold, aiMetrics.similarity_candidate_cap)}
            detail={`warn ${aiMetrics.similarity_candidate_warn_threshold ?? '-'} | cap ${aiMetrics.similarity_candidate_cap ?? '-'}`}
          />
        </div>
        <div className="grid gap-2 text-xs text-slate-500 md:grid-cols-2 xl:grid-cols-4">
          <div>AI generations (15m): {aiMetrics.generations_15m ?? 0}</div>
          <div>Fallbacks (15m): {aiMetrics.fallbacks_15m ?? 0}</div>
          <div>Similarity runs (15m): {aiMetrics.similarity_runs_15m ?? 0}</div>
          <div>Last queue sample: {formatDateTime(aiMetrics.last_queue_sample_at)}</div>
        </div>
      </Card>
      <SystemHealthHistoryCharts
        historyData={historyData}
        persistedHistoryData={persistedHistoryData}
        localHistoryData={localHistoryData}
      />
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Scheduler Observability</p>
        <pre className="overflow-auto rounded-xl bg-slate-100 p-3 text-xs dark:bg-slate-800">
          {JSON.stringify(
            {
              scheduler: data?.scheduler || {},
              scheduler_lock: data?.scheduler_lock || {},
              scheduled_notice_dispatch: data?.scheduled_notice_dispatch || {},
              scheduler_metrics: data?.observability?.scheduler_metrics || {},
            },
            null,
            2
          )}
        </pre>
      </Card>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Top Paths (15m)</p>
        {data?.observability?.request_metrics?.top_paths_15m?.length ? (
          <div className="space-y-2">
            {data.observability.request_metrics.top_paths_15m.map((row) => (
              <div key={row.path} className="rounded-xl border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
                <div className="font-medium">{row.path}</div>
                <div className="text-slate-600 dark:text-slate-300">
                  requests={row.requests} | 5xx={row.server_errors} | slow={row.slow_requests}
                </div>
                <div className="text-slate-500">
                  avg={formatDuration(row.avg_duration_ms)} | p95={formatDuration(row.p95_duration_ms)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No recent request metrics yet.</p>
        )}
      </Card>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Collection Counts</p>
        <pre className="overflow-auto rounded-xl bg-slate-100 p-3 text-xs dark:bg-slate-800">{JSON.stringify(data?.collection_counts || {}, null, 2)}</pre>
      </Card>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Slow Query Logs (latest)</p>
        {data?.slow_query_logs?.length ? (
          <div className="space-y-2">
            {data.slow_query_logs.map((row, idx) => (
              <div key={`${row.created_at}-${idx}`} className="rounded-xl border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
                <div className="font-medium">{row.resource || 'unknown'}</div>
                <div className="text-slate-600 dark:text-slate-300">{row.detail || '-'}</div>
                <div className="text-slate-500">{row.created_at ? new Date(row.created_at).toLocaleString() : '-'}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No slow-query logs in last 24h.</p>
        )}
      </Card>
    </div>
  );
}

function CapacityStatus({ label, value, status, detail }) {
  return (
    <div className={`rounded-xl border px-3 py-3 ${statusClasses(status)}`}>
      <div className="text-xs uppercase tracking-wide opacity-80">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide">{status}</div>
      <div className="mt-2 text-xs opacity-80">{detail}</div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </Card>
  );
}
