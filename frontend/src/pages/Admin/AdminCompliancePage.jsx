import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

export default function AdminCompliancePage() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadSummary() {
      setError('');
      try {
        const response = await apiClient.get('/admin/analytics/audit-summary');
        setSummary(response.data || null);
      } catch (err) {
        setError(formatApiError(err, 'Failed to load compliance summary'));
      }
    }
    loadSummary();
  }, []);

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Compliance</h1>
        <p className="text-sm text-slate-500">Audit visibility and governance review workflows.</p>
      </Card>
      <AdminDomainNav />
      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}
      {summary ? (
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="Total (24h)" value={summary.severity?.total} />
          <Metric label="Low (24h)" value={summary.severity?.low} />
          <Metric label="Medium (24h)" value={summary.severity?.medium} />
          <Metric label="High (24h)" value={summary.severity?.high} />
        </div>
      ) : null}
      {summary?.top_actions?.length ? (
        <Card className="space-y-2">
          <h2 className="text-lg font-semibold">Top Audit Actions (24h)</h2>
          <div className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
            {summary.top_actions.map((item) => (
              <div key={item.action_type} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
                <span>{item.action_type}</span>
                <span className="font-semibold">{item.count}</span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
      <Card className="space-y-2">
        <p className="text-sm text-slate-600 dark:text-slate-300">Track platform governance with audit log filters and security events.</p>
        <Link className="btn-primary" to="/audit-logs">Open Audit Logs</Link>
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
