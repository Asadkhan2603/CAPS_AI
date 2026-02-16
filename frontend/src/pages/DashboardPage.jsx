import { useMemo, useState } from 'react';
import { Bell, BookOpenCheck, ChartLine, FileText, Sparkles } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { Link } from 'react-router-dom';
import StatCard from '../components/ui/StatCard';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

const performanceData = [
  { month: 'Jan', avg: 67, submissions: 41 },
  { month: 'Feb', avg: 71, submissions: 48 },
  { month: 'Mar', avg: 73, submissions: 55 },
  { month: 'Apr', avg: 76, submissions: 59 },
  { month: 'May', avg: 79, submissions: 62 },
  { month: 'Jun', avg: 81, submissions: 65 }
];

export default function DashboardPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [showNotice, setShowNotice] = useState(true);

  const roleActions = useMemo(() => {
    if (user?.role === 'admin') {
      return [
        { to: '/courses', label: 'Manage Courses' },
        { to: '/years', label: 'Manage Years' },
        { to: '/classes', label: 'Manage Classes' },
        { to: '/sections', label: 'Manage Sections' },
        { to: '/section-subjects', label: 'Section-Subject Mapping' }
      ];
    }
    return [
      { to: '/students', label: 'Manage Students' },
      { to: '/subjects', label: 'Manage Subjects' },
      { to: '/assignments', label: 'Manage Assignments' },
      { to: '/submissions', label: 'Review Submissions' }
    ];
  }, [user?.role]);

  return (
    <div className="space-y-5 page-fade">
      {showNotice ? (
        <Alert
          title="Urgent Academic Notice"
          message="Internal marks freeze in 48 hours. Review pending submissions and finalize evaluations."
          priority="urgent"
          onDismiss={() => setShowNotice(false)}
        />
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={BookOpenCheck} title="Active Subjects" value="14" hint="+2 this semester" />
        <StatCard icon={FileText} title="Submissions Today" value="87" hint="Across all sections" gradient="from-sky-600 to-cyan-500" />
        <StatCard icon={ChartLine} title="Avg. Performance" value="81%" hint="+4.2% month-over-month" gradient="from-emerald-600 to-lime-500" />
        <StatCard icon={Bell} title="Risk Alerts" value="9" hint="Requires faculty review" gradient="from-rose-600 to-orange-500" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="min-w-0 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Academic Trend</h2>
            <Badge variant="info">Live Analytics</Badge>
          </div>
          <div className="h-72 min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={performanceData}>
                <defs>
                  <linearGradient id="avgGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="month" />
                <Tooltip />
                <Area type="monotone" dataKey="avg" stroke="#4f46e5" fill="url(#avgGradient)" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold">Quick Actions</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Navigate modules and continue operations.</p>
          <div className="mt-4 space-y-2">
            {roleActions.map((action) => (
              <Link key={action.to} to={action.to} className="btn-secondary w-full justify-between">
                {action.label}
                <Sparkles size={14} />
              </Link>
            ))}
          </div>
          <button
            className="btn-primary mt-4 w-full"
            onClick={() =>
              pushToast({ title: 'Synced', description: 'Dashboard data refreshed successfully.', variant: 'success' })
            }
          >
            Refresh Insights
          </button>
        </Card>
      </div>
    </div>
  );
}
