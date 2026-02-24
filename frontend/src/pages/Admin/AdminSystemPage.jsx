import { useEffect, useState } from 'react';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

export default function AdminSystemPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setError('');
      try {
        const response = await apiClient.get('/admin/system/health');
        setData(response.data || null);
      } catch (err) {
        setError(formatApiError(err, 'Failed to load system health'));
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">System Health</h1>
        <p className="text-sm text-slate-500">Runtime health, DB status, and key collection counts.</p>
      </Card>
      <AdminDomainNav />
      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="DB Status" value={data?.db_status || '-'} />
        <Metric label="Uptime" value={formatUptime(data?.uptime_seconds)} />
        <Metric label="Errors (24h)" value={data?.error_count_24h ?? 0} />
        <Metric label="Active Sessions (24h)" value={data?.active_sessions_24h ?? 0} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Metric label="Slow Queries (24h)" value={data?.slow_query_count_24h ?? 0} />
        <Metric label="Timestamp" value={data?.timestamp ? new Date(data.timestamp).toLocaleString() : '-'} />
      </div>
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

function formatUptime(seconds) {
  if (!seconds && seconds !== 0) return '-';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}h ${m}m ${s}s`;
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </Card>
  );
}
