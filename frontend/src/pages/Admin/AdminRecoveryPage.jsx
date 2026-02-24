import { useEffect, useState } from 'react';
import Card from '../../components/ui/Card';
import Table from '../../components/ui/Table';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

const collections = [
  'courses',
  'departments',
  'branches',
  'years',
  'classes',
  'notices',
  'notifications',
  'clubs',
  'club_events',
  'assignments',
  'submissions',
  'evaluations',
  'review_tickets'
];

export default function AdminRecoveryPage() {
  const [collection, setCollection] = useState('notices');
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/admin/recovery', { params: { collection, limit: 200 } });
      setRows(response.data?.items?.[collection] || []);
      setSummary(response.data?.summary || {});
    } catch (err) {
      setRows([]);
      setSummary({});
      setError(formatApiError(err, 'Failed to load recovery items'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [collection]);

  async function restore(row) {
    try {
      await apiClient.patch(`/admin/recovery/${collection}/${row.id}/restore`);
      await load();
    } catch (err) {
      setError(formatApiError(err, 'Restore failed'));
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Recovery</h1>
        <p className="text-sm text-slate-500">Soft-delete restore workflows.</p>
      </Card>
      <AdminDomainNav />
      <Card className="space-y-3">
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="Current Collection" value={collection} />
          <Metric label="Recoverable Rows" value={summary?.[collection] ?? rows.length} />
          <Metric label="Loaded Rows" value={rows.length} />
          <Metric label="Status" value={loading ? 'Loading' : 'Ready'} />
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Collection
            <select className="input ml-2 w-56" value={collection} onChange={(e) => setCollection(e.target.value)}>
              {collections.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <button className="btn-secondary" onClick={load} disabled={loading}>{loading ? 'Loading...' : 'Refresh'}</button>
        </div>
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <Table
          columns={[
            { key: 'id', label: 'ID' },
            { key: 'name', label: 'Name' },
            { key: 'is_deleted', label: 'is_deleted', render: (row) => String(row.is_deleted) },
            { key: 'is_active', label: 'is_active', render: (row) => String(row.is_active) },
            { key: 'deleted_by', label: 'Deleted By', render: (row) => row.deleted_by || '-' },
            { key: 'deleted_at', label: 'Deleted At', render: (row) => (row.deleted_at ? new Date(row.deleted_at).toLocaleString() : '-') }
          ]}
          data={rows}
          rowActions={[{ key: 'restore', label: 'Restore', onClick: restore }]}
        />
      </Card>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value ?? '-'}</p>
    </Card>
  );
}
