import { useEffect, useState } from 'react';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

export default function AdminAnalyticsPage() {
  const [overview, setOverview] = useState({});
  const [metrics, setMetrics] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setError('');
      try {
        const [overviewRes, platformRes] = await Promise.all([
          apiClient.get('/admin/analytics/overview'),
          apiClient.get('/admin/analytics/platform')
        ]);
        setOverview(overviewRes.data?.overview || {});
        setMetrics(platformRes.data?.metrics || {});
      } catch (err) {
        setError(formatApiError(err, 'Failed to load analytics'));
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Admin Analytics</h1>
        <p className="text-sm text-slate-500">Platform-level analytics and operational indicators.</p>
      </Card>
      <AdminDomainNav />
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
        <Metric label="Snapshot Date" value={metrics.date || '-'} />
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
