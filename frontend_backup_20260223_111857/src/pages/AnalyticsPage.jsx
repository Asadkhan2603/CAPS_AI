import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Card from '../components/ui/Card';
import StatCard from '../components/ui/StatCard';
import { apiClient } from '../services/apiClient';

export default function AnalyticsPage() {
  const [role, setRole] = useState('');
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadSummary() {
      setLoading(true);
      setError('');
      try {
        const response = await apiClient.get('/analytics/summary');
        setRole(response.data?.role || '');
        setSummary(response.data?.summary || {});
      } catch (err) {
        const detail = err?.response?.data?.detail || 'Failed to load analytics';
        setError(String(detail));
      } finally {
        setLoading(false);
      }
    }

    loadSummary();
  }, []);

  const entries = useMemo(
    () =>
      Object.entries(summary).map(([key, value]) => ({
        label: key.replaceAll('_', ' '),
        value: Number(value) || 0
      })),
    [summary]
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-2">
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Role scope: {role || '-'}</p>
      </Card>

      {loading ? <Card><p className="text-sm text-slate-500">Loading analytics...</p></Card> : null}
      {error ? <Card><p className="text-sm text-rose-600">{error}</p></Card> : null}

      {!loading && !error ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {entries.slice(0, 8).map((item) => (
              <StatCard key={item.label} title={item.label} value={item.value} />
            ))}
          </div>

          <Card className="min-w-0">
            <h2 className="mb-4 text-lg font-semibold">Summary Distribution</h2>
            <div className="h-80 min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={entries}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis dataKey="label" hide />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}

