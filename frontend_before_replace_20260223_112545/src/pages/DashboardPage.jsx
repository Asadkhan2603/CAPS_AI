import { useEffect, useMemo, useState } from 'react';
import { Bell, BookOpenCheck, ChartLine, FileText, Sparkles } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { Link } from 'react-router-dom';
import StatCard from '../components/ui/StatCard';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import TeacherClassTiles from '../components/ui/TeacherClassTiles';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/apiClient';
import { getTeacherSectionsAnalytics } from '../services/sectionsApi';
import { canAccessFeature } from '../utils/permissions';
import { FEATURE_ACCESS } from '../config/featureAccess';

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
  const [summary, setSummary] = useState({});
  const [teacherTiles, setTeacherTiles] = useState([]);
  const [urgentNotices, setUrgentNotices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const roleActions = useMemo(() => {
    if (user?.role === 'admin') {
      return [
        { to: '/analytics', label: 'Analytics' },
        { to: '/courses', label: 'Manage Courses' },
        { to: '/departments', label: 'Manage Departments' },
        { to: '/branches', label: 'Manage Branches' },
        { to: '/years', label: 'Manage Years' },
        { to: '/sections', label: 'Manage Sections' },
        { to: '/users', label: 'Manage Users' }
      ];
    }
    if (user?.role === 'student') {
      return [
        { to: '/submissions', label: 'My Submissions' },
        { to: '/evaluations', label: 'My Evaluations' },
        { to: '/club-events', label: 'Club Events' },
        { to: '/notices', label: 'Notices' },
        { to: '/history', label: 'My History' }
      ];
    }
    return [
      { to: '/analytics', label: 'Analytics' },
      { to: '/students', label: 'Manage Students' },
      { to: '/subjects', label: 'Manage Subjects' },
      { to: '/assignments', label: 'Manage Assignments' },
      { to: '/submissions', label: 'Review Submissions' }
    ];
  }, [user?.role]);

  async function loadDashboardData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    try {
      const teacherTilesRequest = user?.role === 'teacher'
        ? getTeacherSectionsAnalytics()
        : Promise.resolve({ data: { items: [] } });
      const [summaryResp, tilesResp, noticesResp] = await Promise.all([
        apiClient.get('/analytics/summary'),
        teacherTilesRequest,
        apiClient.get('/notices/', { params: { priority: 'urgent', limit: 3 } })
      ]);
      setSummary(summaryResp.data?.summary || {});
      setTeacherTiles(tilesResp.data?.items || []);
      setUrgentNotices(noticesResp.data || []);
      setLastUpdated(new Date());
    } catch {
      setSummary({});
      setTeacherTiles([]);
      setUrgentNotices([]);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    loadDashboardData(true);
  }, [user?.role]);

  const statItems = useMemo(() => {
    const value = (key) => String(summary[key] ?? 0);
    const withAccess = (item) => {
      if (!item.featureKey) return item;
      if (!canAccessFeature(user, FEATURE_ACCESS[item.featureKey])) {
        return { ...item, to: undefined };
      }
      return item;
    };

    if (user?.role === 'admin') {
      return [
        withAccess({ title: 'Users', value: value('users'), hint: 'Open user management', to: '/users', featureKey: 'users' }),
        withAccess({ title: 'Students', value: value('students'), hint: 'Open students', to: '/students', featureKey: 'students' }),
        withAccess({ title: 'Assignments', value: value('assignments'), hint: 'Open assignments', to: '/assignments', featureKey: 'assignments' }),
        withAccess({ title: 'Similarity Flags', value: value('similarity_flags'), hint: 'Open analytics', to: '/analytics', featureKey: 'analytics' })
      ];
    }
    if (user?.role === 'student') {
      return [
        withAccess({ title: 'My Submissions', value: value('total_submissions'), hint: 'Go to submissions', to: '/submissions', featureKey: 'submissions' }),
        withAccess({ title: 'My Evaluations', value: value('total_evaluations'), hint: 'Go to evaluations', to: '/evaluations', featureKey: 'evaluations' }),
        withAccess({ title: 'Pending Reviews', value: value('pending_reviews'), hint: 'Track review status', to: '/submissions', featureKey: 'submissions' }),
        withAccess({ title: 'Urgent Notices', value: String(urgentNotices.length), hint: 'Read urgent notices', to: '/notices', featureKey: 'notices' })
      ];
    }
    return [
      withAccess({ title: 'My Assignments', value: value('my_assignments'), hint: 'Open assignments', to: '/assignments', featureKey: 'assignments' }),
      withAccess({ title: 'My Submissions', value: value('my_submissions'), hint: 'Open submissions', to: '/submissions', featureKey: 'submissions' }),
      withAccess({ title: 'My Evaluations', value: value('my_evaluations'), hint: 'Open evaluations', to: '/evaluations', featureKey: 'evaluations' }),
      withAccess({ title: 'Similarity Alerts', value: value('my_similarity_flags'), hint: 'Open analytics', to: '/analytics', featureKey: 'analytics' })
    ];
  }, [summary, urgentNotices.length, user]);

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
        <StatCard icon={BookOpenCheck} title={statItems[0]?.title} value={statItems[0]?.value} hint={statItems[0]?.hint} to={statItems[0]?.to} />
        <StatCard icon={FileText} title={statItems[1]?.title} value={statItems[1]?.value} hint={statItems[1]?.hint} to={statItems[1]?.to} gradient="from-sky-600 to-cyan-500" />
        <StatCard icon={ChartLine} title={statItems[2]?.title} value={statItems[2]?.value} hint={statItems[2]?.hint} to={statItems[2]?.to} gradient="from-emerald-600 to-lime-500" />
        <StatCard icon={Bell} title={statItems[3]?.title} value={statItems[3]?.value} hint={statItems[3]?.hint} to={statItems[3]?.to} gradient="from-rose-600 to-orange-500" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="min-w-0 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Academic Trend</h2>
            <div className="flex items-center gap-2">
              <Badge variant="info">Live Analytics</Badge>
              {lastUpdated ? (
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  Updated {lastUpdated.toLocaleTimeString()}
                </span>
              ) : null}
            </div>
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
            onClick={async () => {
              await loadDashboardData();
              pushToast({ title: 'Synced', description: 'Dashboard data refreshed successfully.', variant: 'success' });
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh Insights'}
          </button>
        </Card>
      </div>

      {urgentNotices.length ? (
        <Card className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Urgent Notices</h2>
            <Badge variant="danger">Priority</Badge>
          </div>
          <div className="space-y-2">
            {urgentNotices.map((notice) => (
              <div key={notice.id} className="rounded-xl border border-rose-200 bg-rose-50 p-3 dark:border-rose-900/40 dark:bg-rose-950/30">
                <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">{notice.title}</p>
                <p className="mt-1 text-sm text-rose-700/90 dark:text-rose-200">{notice.message}</p>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {user?.role === 'teacher' ? <TeacherClassTiles items={teacherTiles} /> : null}
    </div>
  );
}
