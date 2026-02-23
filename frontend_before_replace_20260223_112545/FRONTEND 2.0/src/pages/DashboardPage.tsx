import React, { useEffect, useMemo, useState } from 'react';
import { BookOpen, CheckCircle2, Clock, Users } from 'lucide-react';
import { Card, Badge } from '../components/ui';
import { apiClient } from '../services/apiClient';

interface SummaryMap {
  [key: string]: number | string | undefined;
}

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<SummaryMap>({});
  const [notices, setNotices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [summaryRes, noticesRes] = await Promise.all([
          apiClient.get('/analytics/summary'),
          apiClient.get('/notices/', { params: { priority: 'urgent', limit: 5 } })
        ]);
        setSummary(summaryRes.data?.summary || {});
        setNotices(noticesRes.data || []);
      } catch {
        setSummary({});
        setNotices([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const cards = useMemo(() => [
    { label: 'Users', value: String(summary.users ?? summary.total_users ?? 0), icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Assignments', value: String(summary.assignments ?? summary.my_assignments ?? 0), icon: BookOpen, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Evaluations', value: String(summary.total_evaluations ?? summary.my_evaluations ?? 0), icon: CheckCircle2, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Pending', value: String(summary.pending_reviews ?? 0), icon: Clock, color: 'text-orange-600', bg: 'bg-orange-50' }
  ], [summary]);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard Overview</h1>
        <p className="text-slate-500">Live summary from backend APIs.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((card) => (
          <div key={card.label} className="panel flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">{card.label}</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{loading ? '...' : card.value}</h3>
            </div>
            <div className={`${card.bg} p-3 rounded-xl`}>
              <card.icon className={card.color} size={24} />
            </div>
          </div>
        ))}
      </div>

      <Card title="Urgent Notices" subtitle="Latest urgent announcements">
        {notices.length === 0 ? (
          <p className="text-sm text-slate-500">No urgent notices.</p>
        ) : (
          <div className="space-y-3">
            {notices.map((notice: any) => (
              <div key={notice.id} className="p-3 rounded-xl border border-slate-200 bg-slate-50">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-slate-900">{notice.title}</p>
                  <Badge variant="warning">{notice.priority || 'normal'}</Badge>
                </div>
                <p className="text-sm text-slate-600 mt-1">{notice.message}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
