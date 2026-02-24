import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

export default function AdminDashboardPage() {
  const [summary, setSummary] = useState({});
  const [system, setSystem] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setError('');
      try {
        const [summaryRes, systemRes] = await Promise.all([
          apiClient.get('/admin/analytics/overview'),
          apiClient.get('/admin/system/health')
        ]);
        setSummary(summaryRes.data?.overview || {});
        setSystem(systemRes.data || null);
      } catch (err) {
        setError(formatApiError(err, 'Failed to load admin dashboard'));
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Admin Control Plane</h1>
        <p className="text-sm text-slate-500">Domain-based admin panel aligned with admin.md v2 architecture.</p>
      </Card>
      <AdminDomainNav />
      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Users" value={summary.total_users} />
        <Metric label="Students" value={summary.active_students} />
        <Metric label="Assignments" value={summary.assignments_total} />
        <Metric label="Clubs" value={summary.active_clubs} />
      </div>
      <Card className="space-y-2">
        <h2 className="text-lg font-semibold">System Health</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">Database: {system?.db_status || '-'}</p>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary" to="/admin/governance">Go Governance</Link>
          <Link className="btn-secondary" to="/admin/academic-structure">Go Academic Structure</Link>
          <Link className="btn-secondary" to="/admin/operations">Go Operations</Link>
          <Link className="btn-secondary" to="/admin/clubs">Go Clubs</Link>
        </div>
      </Card>
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
