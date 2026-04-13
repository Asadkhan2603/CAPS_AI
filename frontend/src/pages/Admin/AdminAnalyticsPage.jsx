import { useEffect, useState } from 'react';
import Card from '../../components/ui/Card';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

export default function AdminAnalyticsPage() {
  const [overview, setOverview] = useState({});
  const [metrics, setMetrics] = useState({});
  const [snapshotMeta, setSnapshotMeta] = useState({ servedFrom: '-', ageHours: null });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    void loadAnalytics();
  }, []);

  async function loadAnalytics(forceRefresh = false) {
    setError('');
    setIsRefreshing(true);
    try {
      const response = await apiClient.get('/admin/analytics/bootstrap', {
        params: forceRefresh ? { refresh: true } : undefined,
      });
      setOverview(response.data?.overview || {});
      setMetrics(response.data?.metrics || {});
      setSnapshotMeta({
        servedFrom: response.data?.snapshot_served_from || '-',
        ageHours: response.data?.snapshot_age_hours ?? null,
      });
    } catch (err) {
      setError(formatApiError(err, 'Failed to load analytics'));
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Admin Analytics</h1>
            <p className="text-sm text-slate-500">Platform-level analytics and operational indicators.</p>
          </div>
          <button type="button" className="btn-secondary" onClick={() => void loadAnalytics(true)}>
            {isRefreshing ? 'Refreshing...' : 'Refresh Snapshot'}
          </button>
        </div>
        <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-3">
          <div>Snapshot source: {snapshotMeta.servedFrom}</div>
          <div>Snapshot age (hours): {snapshotMeta.ageHours ?? '-'}</div>
          <div>Snapshot date: {metrics.date || '-'}</div>
        </div>
      </Card>
      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Total Users" value={overview.total_users} />
        <Metric label="Active Students" value={overview.active_students} />
        <Metric label="Active Clubs" value={overview.active_clubs} />
        <Metric label="Events This Week" value={overview.events_this_week} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="DAU (24h)" value={metrics.daily_active_users} />
        <Metric label="Login Count (24h)" value={metrics.login_count_24h} />
        <Metric label="Assignment Completion %" value={metrics.assignment_completion_pct} />
        <Metric label="Club Participation %" value={metrics.club_participation_pct} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="Event Attendance %" value={metrics.event_attendance_pct} />
        <Metric label="Review Ticket SLA (hrs)" value={metrics.review_ticket_sla_hours} />
        <Metric label="Pending Review Tickets" value={metrics.pending_review_tickets} />
        <Metric label="System Errors (24h)" value={overview.system_errors_24h} />
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value ?? 0}</p>
    </Card>
  );
}
