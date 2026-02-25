import { useEffect, useMemo, useState } from 'react';
import { Bell, BookOpenCheck, ChartLine, FileText, Sparkles, ArrowRight, CircleCheck, Clock3, ShieldAlert, CalendarClock, Download, BookOpen } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
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
  const [studentEvaluations, setStudentEvaluations] = useState([]);
  const [studentAssignments, setStudentAssignments] = useState([]);
  const [studentSubmissions, setStudentSubmissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const roleActions = useMemo(() => {
    if (user?.role === 'admin') {
      return [
        { to: '/analytics', label: 'Analytics' },
        { to: '/faculties', label: 'Manage Faculties' },
        { to: '/departments', label: 'Manage Departments' },
        { to: '/programs', label: 'Manage Programs' },
        { to: '/batches', label: 'Manage Batches' },
        { to: '/semesters', label: 'Manage Semesters' },
        { to: '/sections', label: 'Manage Sections' },
        { to: '/users', label: 'Manage Users' }
      ];
    }
    if (user?.role === 'student') {
      return [
        { to: '/submissions', label: 'My Submissions' },
        { to: '/evaluations', label: 'My Evaluations' },
        { to: '/clubs', label: 'Clubs Hub' },
        { to: '/communication/announcements', label: 'Notices' },
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

  const studentIdentity = useMemo(() => {
    const profile = user?.profile || {};
    const email = user?.email || '';
    const enrollment = profile.enrollment_number || (email.includes('@') ? email.split('@')[0] : user?.id) || '-';
    return {
      department: profile.department || '-',
      branch: profile.branch || profile.branch_name || '-',
      enrollment
    };
  }, [user]);

  async function loadDashboardData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    try {
      const teacherTilesRequest = user?.role === 'teacher'
        ? getTeacherSectionsAnalytics()
        : Promise.resolve({ data: { items: [] } });
      const studentEvaluationsRequest = user?.role === 'student'
        ? apiClient.get('/evaluations/', { params: { skip: 0, limit: 5 } })
        : Promise.resolve({ data: [] });
      const studentAssignmentsRequest = user?.role === 'student'
        ? apiClient.get('/assignments/', { params: { skip: 0, limit: 300 } })
        : Promise.resolve({ data: [] });
      const studentSubmissionsRequest = user?.role === 'student'
        ? apiClient.get('/submissions/', { params: { skip: 0, limit: 300 } })
        : Promise.resolve({ data: [] });
      const [summaryResp, tilesResp, noticesResp, studentEvaluationsResp, studentAssignmentsResp, studentSubmissionsResp] =
        await Promise.allSettled([
          apiClient.get('/analytics/summary'),
          teacherTilesRequest,
          apiClient.get('/notices/', { params: { priority: 'urgent', limit: 3 } }),
          studentEvaluationsRequest,
          studentAssignmentsRequest,
          studentSubmissionsRequest
        ]);

      setSummary(summaryResp.status === 'fulfilled' ? summaryResp.value.data?.summary || {} : {});
      setTeacherTiles(tilesResp.status === 'fulfilled' ? tilesResp.value.data?.items || [] : []);
      setUrgentNotices(noticesResp.status === 'fulfilled' ? noticesResp.value.data || [] : []);
      setStudentEvaluations(studentEvaluationsResp.status === 'fulfilled' ? studentEvaluationsResp.value.data || [] : []);
      setStudentAssignments(studentAssignmentsResp.status === 'fulfilled' ? studentAssignmentsResp.value.data || [] : []);
      setStudentSubmissions(studentSubmissionsResp.status === 'fulfilled' ? studentSubmissionsResp.value.data || [] : []);
      setLastUpdated(new Date());
    } catch {
      setSummary({});
      setTeacherTiles([]);
      setUrgentNotices([]);
      setStudentEvaluations([]);
      setStudentAssignments([]);
      setStudentSubmissions([]);
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

  const studentSubjectTrendByMonth = useMemo(() => {
    if (user?.role !== 'student') return { data: [], subjects: [] };
    const assignmentById = new Map(studentAssignments.map((item) => [item.id, item]));
    const monthSubjectAgg = new Map();
    const subjectTotals = new Map();

    studentEvaluations.forEach((evaluation) => {
      const submission = studentSubmissions.find((item) => item.id === evaluation.submission_id);
      const assignment = submission ? assignmentById.get(submission.assignment_id) : null;
      const subject = assignment?.subject_id || 'Unassigned';
      const month = evaluation?.created_at
        ? new Date(evaluation.created_at).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
        : 'Unknown';
      const key = `${month}::${subject}`;
      if (!monthSubjectAgg.has(key)) {
        monthSubjectAgg.set(key, { month, subject, total: 0, count: 0 });
      }
      const node = monthSubjectAgg.get(key);
      node.total += Number(evaluation?.grand_total || 0);
      node.count += 1;
      subjectTotals.set(subject, (subjectTotals.get(subject) || 0) + 1);
    });

    const topSubjects = Array.from(subjectTotals.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map((item) => item[0]);

    const monthMap = new Map();
    for (const node of monthSubjectAgg.values()) {
      if (!topSubjects.includes(node.subject)) continue;
      if (!monthMap.has(node.month)) monthMap.set(node.month, { month: node.month });
      monthMap.get(node.month)[node.subject] = Number((node.total / node.count).toFixed(2));
    }

    return {
      data: Array.from(monthMap.values()),
      subjects: topSubjects
    };
  }, [studentAssignments, studentEvaluations, studentSubmissions, user?.role]);

  const studentDeadlines = useMemo(() => {
    if (user?.role !== 'student') return [];
    const now = Date.now();
    return studentAssignments
      .filter((item) => item?.due_date)
      .map((item) => {
        const dueTs = new Date(item.due_date).getTime();
        const hoursLeft = Math.floor((dueTs - now) / (1000 * 60 * 60));
        let urgency = 'normal';
        if (hoursLeft < 0) urgency = 'overdue';
        else if (hoursLeft <= 24) urgency = 'high';
        else if (hoursLeft <= 72) urgency = 'medium';
        return {
          id: item.id,
          title: item.title,
          dueDate: item.due_date,
          urgency,
          hoursLeft
        };
      })
      .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime())
      .slice(0, 8);
  }, [studentAssignments, user?.role]);

  const studentTimetable = useMemo(() => {
    if (user?.role !== 'student') return [];
    const subjects = Array.from(
      new Set(
        studentAssignments
          .map((item) => item?.subject_id)
          .filter(Boolean)
      )
    );
    const labels = subjects.length ? subjects : ['Study Lab', 'Core Subject', 'Project Work'];
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const slots = ['09:00-10:00', '11:00-12:00', '14:00-15:00'];

    return days.map((day, index) => ({
      day,
      sessions: slots.map((slot, slotIndex) => ({
        time: slot,
        subject: labels[(index + slotIndex) % labels.length]
      }))
    }));
  }, [studentAssignments, user?.role]);

  const todayTimetable = useMemo(() => {
    const dayName = new Date().toLocaleDateString(undefined, { weekday: 'long' });
    return studentTimetable.find((item) => item.day === dayName) || studentTimetable[0] || { day: '-', sessions: [] };
  }, [studentTimetable]);

  const nextClass = useMemo(() => {
    const nowMinutes = (() => {
      const now = new Date();
      return now.getHours() * 60 + now.getMinutes();
    })();
    const sessions = todayTimetable.sessions || [];
    const upcoming = sessions.find((session) => {
      const [start] = String(session.time || '').split('-');
      const [h, m] = start.split(':').map((v) => Number(v || 0));
      return h * 60 + m >= nowMinutes;
    });
    return upcoming || sessions[0] || null;
  }, [todayTimetable]);

  function exportCsv(filename, rows) {
    if (!rows.length) {
      pushToast({ title: 'No data', description: 'Nothing to export right now.', variant: 'info' });
      return;
    }
    const headers = Object.keys(rows[0]);
    const body = rows.map((row) => headers.map((h) => JSON.stringify(row[h] ?? '')).join(',')).join('\n');
    const csv = `${headers.join(',')}\n${body}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  if (user?.role === 'student') {
    return (
      <div className="space-y-5 page-fade">
        <div className="rounded-3xl border border-slate-200 bg-gradient-to-r from-sky-50 to-indigo-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:to-slate-900">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Student Workspace</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">Welcome back, {user?.full_name?.split(' ')[0] || 'Student'}</h1>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Track submissions, notices, and evaluations in one place.</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900">
                  <p className="text-slate-500">Department</p>
                  <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-100">{studentIdentity.department}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900">
                  <p className="text-slate-500">Branch</p>
                  <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-100">{studentIdentity.branch}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900">
                  <p className="text-slate-500">Enrollment</p>
                  <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-100">{studentIdentity.enrollment}</p>
                </div>
              </div>
            </div>
            <Link to="/communication/announcements" className="btn-secondary relative">
              <Bell size={16} /> Notices
              {urgentNotices.length > 0 ? (
                <span className="ml-1 rounded-full bg-rose-600 px-2 py-0.5 text-[10px] font-semibold text-white">
                  {urgentNotices.length}
                </span>
              ) : null}
            </Link>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="!rounded-2xl !border-slate-200 !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">My Submissions</p>
            <p className="mt-1 text-3xl font-bold">{summary.total_submissions ?? 0}</p>
            <Link to="/submissions" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-700 dark:text-brand-300">Open <ArrowRight size={12} /></Link>
          </Card>
          <Card className="!rounded-2xl !border-slate-200 !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">My Evaluations</p>
            <p className="mt-1 text-3xl font-bold">{summary.total_evaluations ?? 0}</p>
            <Link to="/evaluations" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-700 dark:text-brand-300">Open <ArrowRight size={12} /></Link>
          </Card>
          <Card className="!rounded-2xl !border-slate-200 !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Pending Reviews</p>
            <p className="mt-1 text-3xl font-bold">{summary.pending_reviews ?? 0}</p>
            <p className="mt-2 inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400"><Clock3 size={12} /> Awaiting teacher feedback</p>
          </Card>
          <Card className="!rounded-2xl !border-slate-200 !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Urgent Notices</p>
            <p className="mt-1 text-3xl font-bold">{urgentNotices.length}</p>
            <p className="mt-2 inline-flex items-center gap-1 text-xs text-rose-600 dark:text-rose-400"><ShieldAlert size={12} /> Immediate action required</p>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Urgent Notices</h2>
              <Link to="/communication/announcements" className="text-xs font-semibold text-brand-700 dark:text-brand-300">View all</Link>
            </div>
            <div className="space-y-2">
              {urgentNotices.length === 0 ? (
                <p className="text-sm text-slate-500">No urgent notices right now.</p>
              ) : (
                urgentNotices.map((notice) => (
                  <div key={notice.id} className="rounded-xl border border-rose-200 bg-rose-50 p-3 dark:border-rose-900/40 dark:bg-rose-950/25">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">{notice.title}</p>
                      <Badge variant="danger">Urgent</Badge>
                    </div>
                    <p className="mt-1 text-sm text-rose-700/90 dark:text-rose-200">{notice.message}</p>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">Recent Evaluation Status</h2>
            <div className="mt-3 space-y-2">
              {studentEvaluations.length === 0 ? (
                <p className="text-sm text-slate-500">No evaluations available yet.</p>
              ) : (
                studentEvaluations.map((item) => (
                  <div key={item.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                    <p className="text-sm font-semibold">Grade: {item.grade || '-'}</p>
                    <p className="mt-1 text-xs text-slate-500">Total: {item.grand_total ?? 0}</p>
                    <p className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                      <CircleCheck size={12} /> {item.is_finalized ? 'Finalized' : 'In Progress'}
                    </p>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Today Timetable</h2>
              <span className="text-xs text-slate-500">{todayTimetable.day}</span>
            </div>
            <div className="space-y-2">
              {(todayTimetable.sessions || []).map((session) => (
                <div key={`${todayTimetable.day}-${session.time}`} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <p className="text-xs text-slate-500">{session.time}</p>
                  <p className="text-sm font-semibold">{session.subject}</p>
                </div>
              ))}
              {nextClass ? (
                <div className="rounded-xl border border-brand-200 bg-brand-50 p-3 dark:border-brand-800 dark:bg-brand-900/20">
                  <p className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 dark:text-brand-300">
                    <CalendarClock size={12} /> Next Class
                  </p>
                  <p className="mt-1 text-sm">{nextClass.subject} ({nextClass.time})</p>
                </div>
              ) : (
                <p className="text-sm text-slate-500">No class sessions mapped.</p>
              )}
            </div>
          </Card>

          <Card className="xl:col-span-2">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Deadlines Calendar</h2>
              <Link to="/submissions" className="text-xs font-semibold text-brand-700 dark:text-brand-300">Open submissions</Link>
            </div>
            <div className="space-y-2">
              {studentDeadlines.length === 0 ? (
                <p className="text-sm text-slate-500">No assignment deadlines available.</p>
              ) : (
                studentDeadlines.map((item) => (
                  <div
                    key={item.id}
                    className={`rounded-xl border p-3 ${
                      item.urgency === 'overdue'
                        ? 'border-rose-300 bg-rose-50 dark:border-rose-900/40 dark:bg-rose-950/20'
                        : item.urgency === 'high'
                          ? 'border-orange-300 bg-orange-50 dark:border-orange-900/40 dark:bg-orange-950/20'
                          : item.urgency === 'medium'
                            ? 'border-amber-300 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-950/20'
                            : 'border-emerald-300 bg-emerald-50 dark:border-emerald-900/40 dark:bg-emerald-950/20'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold">{item.title}</p>
                      <span className="text-xs">
                        {item.urgency === 'overdue'
                          ? 'Overdue'
                          : item.urgency === 'high'
                            ? 'Due within 24h'
                            : item.urgency === 'medium'
                              ? 'Due within 3 days'
                              : 'Upcoming'}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                      Due: {new Date(item.dueDate).toLocaleString()}
                    </p>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Performance Trend By Subject Over Time</h2>
              <span className="inline-flex items-center gap-1 text-xs text-slate-500"><BookOpen size={12} /> Based on evaluations</span>
            </div>
            <div className="h-72">
              {studentSubjectTrendByMonth.data.length === 0 ? (
                <p className="text-sm text-slate-500">Not enough evaluation data for trend chart yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={studentSubjectTrendByMonth.data}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    {studentSubjectTrendByMonth.subjects.map((subject, index) => (
                      <Line
                        key={subject}
                        type="monotone"
                        dataKey={subject}
                        stroke={['#4f46e5', '#0ea5e9', '#16a34a', '#f97316'][index % 4]}
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold">Download Center</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Export your records as CSV.</p>
            <div className="mt-3 space-y-2">
              <button
                className="btn-secondary w-full justify-between"
                onClick={() =>
                  exportCsv('my-submissions.csv', studentSubmissions.map((item) => ({
                    assignment_id: item.assignment_id,
                    filename: item.original_filename,
                    status: item.status,
                    ai_status: item.ai_status,
                    created_at: item.created_at
                  })))
                }
              >
                Export Submissions <Download size={14} />
              </button>
              <button
                className="btn-secondary w-full justify-between"
                onClick={() =>
                  exportCsv('my-evaluations.csv', studentEvaluations.map((item) => ({
                    submission_id: item.submission_id,
                    grand_total: item.grand_total,
                    grade: item.grade,
                    finalized: item.is_finalized,
                    created_at: item.created_at
                  })))
                }
              >
                Export Evaluations <Download size={14} />
              </button>
              <button
                className="btn-secondary w-full justify-between"
                onClick={() =>
                  exportCsv('my-deadlines.csv', studentDeadlines.map((item) => ({
                    assignment: item.title,
                    due_date: item.dueDate,
                    urgency: item.urgency
                  })))
                }
              >
                Export Deadlines <Download size={14} />
              </button>
            </div>
          </Card>
        </div>

        <Card>
          <h2 className="text-lg font-semibold">Quick Actions</h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {roleActions.map((action) => (
              <Link key={action.to} to={action.to} className="btn-secondary justify-between">
                {action.label}
                <ArrowRight size={14} />
              </Link>
            ))}
          </div>
        </Card>
      </div>
    );
  }

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
