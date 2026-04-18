import { useEffect, useMemo, useState } from 'react';
import { apiClient } from '../../../services/apiClient';
import { formatApiError } from '../../../utils/apiError';

export const AUTO_REFRESH_MS = 30000;

const MAX_LOCAL_SNAPSHOTS = 120;
const STORAGE_KEY = 'caps_admin_system_health_snapshots_v1';

export function useAdminSystemHealth({ pushToast }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [localSnapshots, setLocalSnapshots] = useState(() => loadStoredSnapshots());

  const aiMetrics = data?.observability?.ai_metrics || {};
  const alertRouting = data?.alert_routing || {};
  const alertRouteHistory = data?.alert_route_history || [];
  const clubsMetrics = data?.observability?.clubs_metrics || {};
  const clubsObservabilityRaw = data?.clubs_observability || {};
  const snapshotStore = data?.snapshot_store || {};
  const usersAdminDashboard = data?.users_admin_dashboard || null;
  const usersAdminAlerts = data?.users_admin_alerts || [];

  const historyData = useMemo(
    () =>
      (aiMetrics.history_15m || []).map((point) => ({
        label: point.timestamp
          ? new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          : '-',
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
        label: point.bucket_minute
          ? new Date(point.bucket_minute).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : '-',
        queuedJobs: point.queued_jobs ?? 0,
        oldestAgeSeconds: point.oldest_queued_age_seconds ?? 0,
        fallbackRatePct: point.fallback_rate_pct_15m ?? 0,
        similarityCandidates: point.similarity_candidate_count ?? 0,
        clubRequests: point.club_requests_15m ?? 0,
        clubP95DurationMs: point.club_p95_duration_ms_15m ?? 0,
        retainedRows: point.retained_rows ?? 0,
        prunedDeletedCount: point.last_pruned_deleted_count ?? 0,
      })),
    [data?.snapshot_history]
  );

  const localHistoryData = useMemo(
    () =>
      localSnapshots.map((snapshot) => ({
        label: snapshot.timestamp
          ? new Date(snapshot.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          : '-',
        queuedJobs: snapshot.queuedJobs,
        oldestAgeSeconds: snapshot.oldestAgeSeconds,
        fallbackRatePct: snapshot.fallbackRatePct,
        similarityCandidates: snapshot.similarityCandidates,
        clubRequests: snapshot.clubRequests,
        clubP95DurationMs: snapshot.clubP95DurationMs,
      })),
    [localSnapshots]
  );

  const clubsObservability = useMemo(() => {
    const mapPoint = (point, formatOptions) => ({
      bucketStart: point.bucket_start,
      label: point.bucket_start ? new Date(point.bucket_start).toLocaleString([], formatOptions) : '-',
      clubRequestsAvg: point.club_requests_avg ?? 0,
      clubRequestsPeak: point.club_requests_peak ?? 0,
      clubP95Avg: point.club_p95_duration_ms_avg ?? 0,
      clubP95Peak: point.club_p95_duration_ms_peak ?? 0,
      clubSlowTotal: point.club_slow_requests_total ?? 0,
      clubServerErrorsTotal: point.club_server_errors_total ?? 0,
      pressureLevel: point.pressure_level || 'ok',
      pressureSignal:
        point.pressure_level === 'critical'
          ? 2
          : point.pressure_level === 'warning'
            ? 1
            : 0,
    });
    return {
      summary: clubsObservabilityRaw.summary || {},
      hourly24h: (clubsObservabilityRaw.hourly_24h || []).map((point) =>
        mapPoint(point, { hour: '2-digit', minute: '2-digit' })
      ),
      daily14d: (clubsObservabilityRaw.daily_14d || []).map((point) =>
        mapPoint(point, { month: 'short', day: 'numeric' })
      ),
      recentPressureWindows: (clubsObservabilityRaw.recent_pressure_windows || []).map((point) =>
        mapPoint(point, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      ),
    };
  }, [clubsObservabilityRaw]);

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

  async function loadHealth({ silent, forceRefresh = false }) {
    if (!silent) {
      setError('');
    }
    setIsRefreshing(true);
    try {
      const response = await apiClient.get('/admin/system/health', {
        params: forceRefresh ? { refresh: true } : undefined,
      });
      const payload = response.data || null;
      setData(payload);
      setError('');
      if (payload) {
        setLocalSnapshots((current) => {
          const nextSnapshots = appendSnapshot(current, payload);
          saveStoredSnapshots(nextSnapshots);
          return nextSnapshots;
        });
      }
    } catch (err) {
      const message = formatApiError(err, 'Failed to load system health');
      setError(message);
      if (!silent) {
        pushToast({ title: 'Load failed', description: message, variant: 'error' });
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
      pushToast({ title: 'Export complete', description: 'System health snapshots exported.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Export failed', description: formatApiError(err, 'Failed to export snapshots'), variant: 'error' });
    }
  }

  function clearSnapshots() {
    setLocalSnapshots([]);
    saveStoredSnapshots([]);
    pushToast({ title: 'Local history cleared', description: 'Stored local system health snapshots cleared.', variant: 'success' });
  }

  return {
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
    usersAdminAlerts,
    usersAdminDashboard,
  };
}

function appendSnapshot(existing, payload) {
  const aiMetrics = payload?.observability?.ai_metrics || {};
  const clubsMetrics = payload?.observability?.clubs_metrics || {};
  const next = [
    ...existing,
    {
      timestamp: payload?.timestamp || new Date().toISOString(),
      queuedJobs: aiMetrics.queued_jobs ?? 0,
      oldestAgeSeconds: aiMetrics.oldest_queued_age_seconds ?? 0,
      fallbackRatePct: aiMetrics.fallback_rate_pct_15m ?? 0,
      similarityCandidates: aiMetrics.last_similarity_candidate_count ?? 0,
      clubRequests: clubsMetrics.requests_15m ?? 0,
      clubP95DurationMs: clubsMetrics.p95_duration_ms_15m ?? 0,
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
