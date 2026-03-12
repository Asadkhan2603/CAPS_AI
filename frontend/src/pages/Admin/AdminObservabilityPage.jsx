import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

const AUTO_REFRESH_MS = 30000;

export default function AdminObservabilityPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const requestMetrics = data?.observability?.request_metrics || {};
  const aiMetrics = data?.observability?.ai_metrics || {};
  const snapshotStore = data?.snapshot_store || {};

  const liveHistoryData = useMemo(
    () =>
      (aiMetrics.history_15m || []).map((point) => ({
        label: point.timestamp ? new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-',
        queuedJobs: point.queued_jobs ?? 0,
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
        fallbackRatePct: point.fallback_rate_pct_15m ?? 0,
        similarityCandidates: point.similarity_candidate_count ?? 0,
        retainedRows: point.retained_rows ?? 0,
        prunedDeletedCount: point.last_pruned_deleted_count ?? 0,
      })),
    [data?.snapshot_history]
  );

  useEffect(() => {
    void loadObservability();
  }, []);

  useEffect(() => {
    const handle = window.setInterval(() => {
      void loadObservability({ silent: true });
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(handle);
  }, []);

  async function loadObservability({ silent = false } = {}) {
    if (!silent) {
      setError('');
    }
    setIsRefreshing(true);
    try {
      const response = await apiClient.get('/admin/system/health');
      setData(response.data || null);
      setError('');
    } catch (err) {
      setError(formatApiError(err, 'Failed to load observability dashboard'));
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Observability</h1>
            <p className="text-sm text-slate-500">Dedicated runtime dashboard for request pressure, AI capacity, and snapshot retention.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void loadObservability()}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
            </button>
            <span className="text-xs text-slate-500">Auto-refresh {AUTO_REFRESH_MS / 1000}s</span>
          </div>
        </div>
      </Card>
      <AdminDomainNav />
      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Requests (15m)" value={requestMetrics.requests_15m ?? 0} />
        <Metric label="5xx Rate (15m)" value={formatPercent(requestMetrics.server_error_rate_pct_15m)} />
        <Metric label="P95 (15m)" value={formatDuration(requestMetrics.p95_duration_ms_15m)} />
        <Metric label="Slow Requests (15m)" value={requestMetrics.slow_requests_15m ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="AI Queued Jobs" value={aiMetrics.queued_jobs ?? 0} />
        <Metric label="Oldest AI Job Age" value={formatSeconds(aiMetrics.oldest_queued_age_seconds)} />
        <Metric label="Fallback Rate (15m)" value={formatPercent(aiMetrics.fallback_rate_pct_15m)} />
        <Metric label="Similarity Candidates" value={aiMetrics.last_similarity_candidate_count ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Snapshot Rows" value={snapshotStore.retained_rows ?? 0} />
        <Metric label="Snapshot Cap" value={snapshotStore.max_retained_rows ?? '-'} />
        <Metric label="Last Prune Deleted" value={snapshotStore.last_pruned_deleted_count ?? 0} />
        <Metric label="Retention Bound" value={snapshotStore.is_within_retention_bound === false ? 'Drifted' : 'Within Bound'} />
      </div>
      <Card className="space-y-2">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Operational Alerts</p>
        {data?.alerts?.length ? (
          <div className="space-y-2">
            {data.alerts.map((alert) => (
              <div
                key={alert.code}
                className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100"
              >
                <div className="font-medium">{alert.level?.toUpperCase() || 'INFO'} | {alert.code}</div>
                <div>{alert.message}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-emerald-600 dark:text-emerald-400">No active operational alerts.</p>
        )}
      </Card>
      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Live Queue Depth" empty={!liveHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={liveHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="queuedJobs" stroke="#2563eb" fill="#93c5fd" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Live Fallback Rate" empty={!liveHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={liveHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis width={42} domain={[0, 'dataMax + 5']} />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Fallback Rate']} />
              <Area type="monotone" dataKey="fallbackRatePct" stroke="#d97706" fill="#fcd34d" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Live Similarity Candidates" empty={!liveHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={liveHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="similarityCandidates" stroke="#7c3aed" fill="#c4b5fd" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Persisted Queue Depth" empty={!persistedHistoryData.length}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={persistedHistoryData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis allowDecimals={false} width={42} />
              <Tooltip />
              <Area type="monotone" dataKey="queuedJobs" stroke="#0f766e" fill="#5eead4" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Persisted Fallback Rate" empty={!persistedHistoryData.length}>
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
        <ChartCard title="Persisted Snapshot Rows" empty={!persistedHistoryData.length}>
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
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        <ChartCard title="Persisted Prune Activity" empty={!persistedHistoryData.length}>
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
        <Card className="space-y-2">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Current Observability Notes</p>
          <div className="grid gap-2 text-xs text-slate-500">
            <div>Latest payload: {formatDateTime(data?.timestamp)}</div>
            <div>Last queue sample: {formatDateTime(aiMetrics.last_queue_sample_at)}</div>
            <div>Last prune at: {formatDateTime(snapshotStore.last_pruned_at)}</div>
            <div>Last prune bucket: {snapshotStore.last_pruned_bucket || '-'}</div>
          </div>
        </Card>
      </div>
    </div>
  );
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

function formatDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
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

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </Card>
  );
}
