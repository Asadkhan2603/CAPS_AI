import { useEffect, useMemo, useRef, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts';
import PredictiveOversightPanel from '../components/analytics/PredictiveOversightPanel';
import Card from '../components/ui/Card';
import StatCard from '../components/ui/StatCard';
import SafeResponsiveContainer from '../components/charts/SafeResponsiveContainer';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../services/apiClient';

export default function AnalyticsPage() {
  const { user } = useAuth();
  const predictiveRequestStartedRef = useRef(false);
  const [role, setRole] = useState('');
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [predictiveOverview, setPredictiveOverview] = useState(null);
  const [predictiveLoading, setPredictiveLoading] = useState(false);
  const [predictiveError, setPredictiveError] = useState('');
  const [predictiveUnavailable, setPredictiveUnavailable] = useState(() => {
    try {
      return window.sessionStorage.getItem('caps_ai_predictive_overview_unavailable') === '1';
    } catch {
      return false;
    }
  });

  const canViewPredictiveOversight = useMemo(() => {
    if (user?.role === 'admin') return true;
    if (user?.role !== 'teacher') return false;
    const extensions = user?.extended_roles || [];
    return extensions.includes('year_head') || extensions.includes('class_coordinator');
  }, [user]);

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

  useEffect(() => {
    if (!canViewPredictiveOversight || predictiveUnavailable) {
      setPredictiveOverview(null);
      setPredictiveError('');
      setPredictiveLoading(false);
      predictiveRequestStartedRef.current = false;
      return;
    }
    if (predictiveRequestStartedRef.current) {
      return;
    }

    async function loadPredictiveOverview() {
      predictiveRequestStartedRef.current = true;
      setPredictiveLoading(true);
      setPredictiveError('');
      try {
        const response = await apiClient.get('/analytics/academic/predictive-overview');
        try {
          window.sessionStorage.removeItem('caps_ai_predictive_overview_unavailable');
        } catch {
          // Ignore session storage failures for non-critical analytics hints.
        }
        setPredictiveOverview(response.data || null);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 404) {
          try {
            window.sessionStorage.setItem('caps_ai_predictive_overview_unavailable', '1');
          } catch {
            // Ignore session storage failures for non-critical analytics hints.
          }
          setPredictiveUnavailable(true);
          setPredictiveOverview(null);
          setPredictiveError('');
          return;
        }
        const detail = err?.response?.data?.detail || 'Failed to load predictive oversight';
        setPredictiveError(String(detail));
      } finally {
        setPredictiveLoading(false);
        predictiveRequestStartedRef.current = false;
      }
    }

    loadPredictiveOverview();
  }, [canViewPredictiveOversight, predictiveUnavailable]);

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
              <SafeResponsiveContainer>
                <BarChart data={entries}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis dataKey="label" hide />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </SafeResponsiveContainer>
            </div>
          </Card>

          {canViewPredictiveOversight ? (
            <PredictiveOversightPanel
              overview={predictiveOverview}
              loading={predictiveLoading}
              error={predictiveError}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

