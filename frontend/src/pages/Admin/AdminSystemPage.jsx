import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';
import { useToast } from '../../hooks/useToast';

const AUTO_REFRESH_MS = 30000;
const MAX_LOCAL_SNAPSHOTS = 120;
const STORAGE_KEY = 'caps_admin_system_health_snapshots_v1';

export default function AdminSystemPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [localSnapshots, setLocalSnapshots] = useState(() => loadStoredSnapshots());
  const { pushToast } = useToast();
  const aiMetrics = data?.observability?.ai_metrics || {};
  const snapshotStore = data?.snapshot_store || {};

  const historyData = useMemo(
    () =>
      (aiMetrics.history_15m || []).map((point) => ({
        label: point.timestamp ? new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-',
        queuedJobs: point.queued_jobs ?? 0,
        oldestAgeSeconds: point.oldest_queued_age_seconds ?? 0,
        fallbackRatePct: point.fallback_rate_pct_15m ?? 0,
        similarityCandidates: point.similarity_candidate_count ?? 0,
      })),
    [aiMetrics.history_15m]
  );

  const persistedHistoryData = useMemo(
    () =>
      (data?.snapshot_history || []).map((point) => ({
        label: point.bucket_minute ? new Date(point.bucket_minute).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-',
        queuedJobs: point.queued_jobs ?? 0,
        oldestAgeSeconds: point.oldest_queued_age_seconds ?? 0,
        fallbackRatePct: point.fallback_rate_pct_15m ?? 0,
        similarityCandidates: point.similarity_candidate_count ?? 0,
        retainedRows: point.retained_rows ?? 0,
        prunedDeletedCount: point.last_pruned_deleted_count ?? 0,
      })),
    [data?.snapshot_history]
  );

  const localHistoryData = useMemo(
    () =>
      localSnapshots.map((snapshot) => ({
        label: snapshot.timestamp ? new Date(snapshot.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-',
        queuedJobs: snapshot.queuedJobs,
        oldestAgeSeconds: snapshot.oldestAgeSeconds,
        fallbackRatePct: snapshot.fallbackRatePct,
        similarityCandidates: snapshot.similarityCandidates,
      })),
    [localSnapshots]
  );

  useEffect(() => {
    void loadHealth({ silent: false });
  }, []);

  useEffect(() => {
    if (!isAutoRefresh) return undefined;
    const handle = window.setInterval(() => {
      void loadHealth({ silent: true });
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(handle);
  }, [isAutoRefresh]);

  async function loadHealth({ silent }) {
    if (!silent) {
      setError('');
    }
    setIsRefreshing(true);
    try {
      const response = await apiClient.get('/admin/system/health');
      const payload = response.data || null;
      setData(payload);
      setError('');
      if (payload) {
        const nextSnapshots = appendSnapshot(localSnapshots, payload);
        setLocalSnapshots(nextSnapshots);
        saveStoredSnapshots(nextSnapshots);
      }
    } catch (err) {
      const message = formatApiError(err, 'Failed to load system health');
      setError(message);
      if (!silent) {
        pushToast({ type: 'error', message });
      }
    } finally {
      setIsRefreshing(false);
    }
  }

  async function exportSnapshots() {
    try {
      const payload = {
        exported_at: new Date().toISOString(),
        current: data,
        persisted_snapshots: data?.snapshot_history || [],
        local_snapshots: localSnapshots,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `caps-system-health-${Date.now()}.json`;
      anchor.click();
      window.URL.revokeObjectURL(url);
      pushToast({ type: 'success', message: 'System health snapshots exported.' });
    } catch (err) {
      pushToast({ type: 'error', message: formatApiError(err, 'Failed to export snapshots') });
    }
  }

  function clearSnapshots() {
    setLocalSnapshots([]);
    saveStoredSnapshots([]);
    pushToast({ type: 'success', message: 'Stored local system health snapshots cleared.' });
  }

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
              onClick={() => void loadHealth({ silent: false })}
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
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Requests (15m)" value={data?.observability?.request_metrics?.requests_15m ?? 0} />
        <Metric label="5xx Rate (15m)" value={formatPercent(data?.observability?.request_metrics?.server_error_rate_pct_15m)} />
        <Metric label="P95 (15m)" value={formatDuration(data?.observability?.request_metrics?.p95_duration_ms_15m)} />
        <Metric label="Slow Requests (15m)" value={data?.observability?.request_metrics?.slow_requests_15m ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="AI Queued Jobs" value={aiMetrics.queued_jobs ?? 0} />
        <Metric label="Oldest AI Job Age" value={formatSeconds(aiMetrics.oldest_queued_age_seconds)} />
        <Metric label="AI Fallback Rate (15m)" value={formatPercent(aiMetrics.fallback_rate_pct_15m)} />
        <Metric label="Similarity Candidates" value={aiMetrics.last_similarity_candidate_count ?? 0} />
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
      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Live Queue Depth History" empty={!historyData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={historyData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="queuedJobs" stroke="#2563eb" fill="#93c5fd" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Live Fallback Rate History" empty={!historyData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={historyData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis width={42} domain={[0, 'dataMax + 5']} />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate']} />
              <Area type="monotone" dataKey="fallbackRatePct" stroke="#d97706" fill="#fcd34d" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Live Similarity Candidate History" empty={!historyData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={historyData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="similarityCandidates" stroke="#7c3aed" fill="#c4b5fd" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Persisted Queue History" empty={!persistedHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={persistedHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="queuedJobs" stroke="#0f766e" fill="#5eead4" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Persisted Fallback History" empty={!persistedHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={persistedHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis width={42} domain={[0, 'dataMax + 5']} />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate']} />
              <Area type="monotone" dataKey="fallbackRatePct" stroke="#be123c" fill="#fda4af" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Persisted Similarity History" empty={!persistedHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={persistedHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="similarityCandidates" stroke="#4338ca" fill="#a5b4fc" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        <ChartCard title="Persisted Snapshot Row Count" empty={!persistedHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={persistedHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="retainedRows" stroke="#15803d" fill="#86efac" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Persisted Snapshot Prune Activity" empty={!persistedHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={persistedHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="prunedDeletedCount" stroke="#b91c1c" fill="#fca5a5" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Local Queue Snapshot Retention" empty={!localHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={localHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="queuedJobs" stroke="#0369a1" fill="#7dd3fc" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Local Fallback Snapshot Retention" empty={!localHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={localHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis width={42} domain={[0, 'dataMax + 5']} />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate']} />
              <Area type="monotone" dataKey="fallbackRatePct" stroke="#7c2d12" fill="#fdba74" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Local Similarity Snapshot Retention" empty={!localHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={localHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="similarityCandidates" stroke="#581c87" fill="#d8b4fe" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Scheduler Observability</p>
        <pre className="overflow-auto rounded-xl bg-slate-100 p-3 text-xs dark:bg-slate-800">
          {JSON.stringify(
            {
              scheduler: data?.scheduler || {},
              scheduler_lock: data?.scheduler_lock || {},
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

function appendSnapshot(existing, payload) {
  const aiMetrics = payload?.observability?.ai_metrics || {};
  const next = [
    ...existing,
    {
      timestamp: payload?.timestamp || new Date().toISOString(),
      queuedJobs: aiMetrics.queued_jobs ?? 0,
      oldestAgeSeconds: aiMetrics.oldest_queued_age_seconds ?? 0,
      fallbackRatePct: aiMetrics.fallback_rate_pct_15m ?? 0,
      similarityCandidates: aiMetrics.last_similarity_candidate_count ?? 0,
    },
  ];
  return next.slice(-MAX_LOCAL_SNAPSHOTS);
}

function loadStoredSnapshots() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(-MAX_LOCAL_SNAPSHOTS) : [];
  } catch {
    return [];
  }
}

function saveStoredSnapshots(items) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(-MAX_LOCAL_SNAPSHOTS)));
  } catch {
    // Ignore localStorage failures in the health view.
  }
}

function formatUptime(seconds) {
  if (!seconds && seconds !== 0) return '-';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}h ${m}m ${s}s`;
}

function formatDuration(value) {
  if (value === null || value === undefined) return '-';
  return `${value} ms`;
}

function formatPercent(value) {
  if (value === null || value === undefined) return '-';
  return `${Number(value).toFixed(2)}%`;
}

function formatSeconds(value) {
  if (value === null || value === undefined) return '-';
  if (value < 60) return `${value}s`;
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}m ${seconds}s`;
}

function formatMinutes(value) {
  if (value === null || value === undefined) return '-';
  if (value < 60) return `${value}m`;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
}

function formatDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function pickBudgetStatus(value, warning, critical) {
  if (value === null || value === undefined) return 'unknown';
  if (critical !== null && critical !== undefined && value >= critical) return 'critical';
  if (warning !== null && warning !== undefined && value >= warning) return 'warning';
  return 'ok';
}

function statusClasses(status) {
  if (status === 'critical') {
    return 'border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100';
  }
  if (status === 'warning') {
    return 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100';
  }
  if (status === 'ok') {
    return 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100';
  }
  return 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200';
}

function ChartCard({ title, children, empty }) {
  return (
    <Card className="space-y-3">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">{title}</p>
      <div className="h-56 min-w-0">
        {empty ? <p className="text-sm text-slate-500">No recent history yet.</p> : children}
      </div>
    </Card>
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
