import { useEffect, useMemo, useState } from 'react';
import { Bell, BookOpenCheck, ChartLine, FileText, Sparkles, ArrowRight, Clock3, ShieldAlert, CalendarClock } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { Link } from 'react-router-dom';
import StatCard from '../components/ui/StatCard';
import Card from '../components/ui/Card';
import Alert from '../components/ui/Alert';
import Badge from '../components/ui/Badge';
import TeacherClassTiles from '../components/ui/TeacherClassTiles';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/apiClient';
import { getTeacherSectionsAnalytics } from '../services/sectionsApi';
import { canAccessFeature } from '../utils/permissions';
import { formatApiError } from '../utils/apiError';
import { FEATURE_ACCESS } from '../config/featureAccess';

const performanceData = [
  { month: 'Jan', avg: 67, submissions: 41 },
  { month: 'Feb', avg: 71, submissions: 48 },
  { month: 'Mar', avg: 73, submissions: 55 },
  { month: 'Apr', avg: 76, submissions: 59 },
  { month: 'May', avg: 79, submissions: 62 },
  { month: 'Jun', avg: 81, submissions: 65 }
];
const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function isTruthyEligibility(value) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value === 1;
  if (typeof value === 'string') {
    return ['1', 'true', 'yes', 'eligible', 'active', 'enabled'].includes(value.trim().toLowerCase());
  }
  return false;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { isDark } = useTheme();
  const { pushToast } = useToast();
  const [showNotice, setShowNotice] = useState(true);
  const [summary, setSummary] = useState({});
  const [teacherTiles, setTeacherTiles] = useState([]);
  const [urgentNotices, setUrgentNotices] = useState([]);
  const [studentAssignments, setStudentAssignments] = useState([]);
  const [studentSubmissions, setStudentSubmissions] = useState([]);
  const [studentClassSlots, setStudentClassSlots] = useState([]);
  const [studentOfferings, setStudentOfferings] = useState([]);
  const [internshipStatus, setInternshipStatus] = useState(null);
  const [internshipBusy, setInternshipBusy] = useState(false);
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
        { to: '/attendance-records', label: 'Attendance' },
        { to: '/communication/announcements', label: 'Announcements' },
        { to: '/profile', label: 'My Profile' }
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
      academicTrack: profile.branch || profile.specialization || profile.program || '-',
      enrollment
    };
  }, [user]);

  const hasInternshipEligibilityHint = useMemo(() => {
    const profile = user?.profile || {};
    const roleScope = user?.role_scope || {};
    const candidates = [
      profile.internship_eligible,
      profile.is_internship_eligible,
      profile.has_internship,
      profile.internship_enabled,
      profile.internship_status,
      roleScope.internship_eligible,
      roleScope.internship?.eligible,
      roleScope.student?.internship_eligible
    ];
    return candidates.some(isTruthyEligibility);
  }, [user]);

  async function loadDashboardData(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    try {
      const teacherTilesRequest = user?.role === 'teacher'
        ? getTeacherSectionsAnalytics()
        : Promise.resolve({ data: { items: [] } });
      const studentAssignmentsRequest = user?.role === 'student'
        ? apiClient.get('/assignments/', { params: { skip: 0, limit: 300 } })
        : Promise.resolve({ data: [] });
      const studentSubmissionsRequest = user?.role === 'student'
        ? apiClient.get('/submissions/', { params: { skip: 0, limit: 300 } })
        : Promise.resolve({ data: [] });
      const studentClassSlotsRequest = user?.role === 'student'
        ? apiClient.get('/class-slots/my')
        : Promise.resolve({ data: [] });
      const studentOfferingsRequest = user?.role === 'student'
        ? apiClient.get('/course-offerings/', { params: { skip: 0, limit: 100 } })
        : Promise.resolve({ data: [] });
      const internshipStatusRequest = user?.role === 'student'
        ? apiClient.get('/attendance-records/internship/status')
        : Promise.resolve({ data: null });
      const [
        summaryResp,
        tilesResp,
        noticesResp,
        studentAssignmentsResp,
        studentSubmissionsResp,
        studentClassSlotsResp,
        studentOfferingsResp,
        internshipStatusResp
      ] =
        await Promise.allSettled([
          apiClient.get('/analytics/summary'),
          teacherTilesRequest,
          apiClient.get('/notices/', { params: { priority: 'urgent', limit: 3 } }),
          studentAssignmentsRequest,
          studentSubmissionsRequest,
          studentClassSlotsRequest,
          studentOfferingsRequest,
          internshipStatusRequest
        ]);

      setSummary(summaryResp.status === 'fulfilled' ? summaryResp.value.data?.summary || {} : {});
      setTeacherTiles(tilesResp.status === 'fulfilled' ? tilesResp.value.data?.items || [] : []);
      setUrgentNotices(noticesResp.status === 'fulfilled' ? noticesResp.value.data || [] : []);
      setStudentAssignments(studentAssignmentsResp.status === 'fulfilled' ? studentAssignmentsResp.value.data || [] : []);
      setStudentSubmissions(studentSubmissionsResp.status === 'fulfilled' ? studentSubmissionsResp.value.data || [] : []);
      setStudentClassSlots(studentClassSlotsResp.status === 'fulfilled' ? studentClassSlotsResp.value.data || [] : []);
      setStudentOfferings(studentOfferingsResp.status === 'fulfilled' ? studentOfferingsResp.value.data || [] : []);
      setInternshipStatus(internshipStatusResp.status === 'fulfilled' ? internshipStatusResp.value.data || null : null);
      setLastUpdated(new Date());
    } catch {
      setSummary({});
      setTeacherTiles([]);
      setUrgentNotices([]);
      setStudentAssignments([]);
      setStudentSubmissions([]);
      setStudentClassSlots([]);
      setStudentOfferings([]);
      setInternshipStatus(null);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  async function handleInternshipAction(action) {
    setInternshipBusy(true);
    try {
      if (action === 'clock_in') {
        await apiClient.post('/attendance-records/internship/clock-in', { note: 'Student internship clock-in' });
      } else {
        await apiClient.post('/attendance-records/internship/clock-out', { note: 'Student internship clock-out' });
      }
      const response = await apiClient.get('/attendance-records/internship/status');
      setInternshipStatus(response.data || null);
      pushToast({
        title: action === 'clock_in' ? 'Internship started' : 'Internship ended',
        description: action === 'clock_in' ? 'Clock-in recorded.' : 'Clock-out recorded.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Internship update failed',
        description: formatApiError(err, 'Could not update internship session'),
        variant: 'error'
      });
    } finally {
      setInternshipBusy(false);
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
    const offeringMap = new Map(studentOfferings.map((item) => [item.id, item]));
    const grouped = {};
    for (const slot of studentClassSlots) {
      const day = slot.day || 'Unknown';
      const offering = offeringMap.get(slot.course_offering_id) || {};
      if (!grouped[day]) grouped[day] = [];
      grouped[day].push({
        time: `${slot.start_time}-${slot.end_time}`,
        subject: offering.subject_name || offering.subject_code || offering.subject_id || 'Subject',
        teacher: offering.teacher_name || offering.teacher_user_id || 'Teacher',
        room: slot.room_code || '-',
        type: offering.offering_type || '-',
        group: offering.group_name || ''
      });
    }
    return Object.entries(grouped)
      .map(([day, sessions]) => ({
        day,
        sessions: [...sessions].sort((a, b) => String(a.time).localeCompare(String(b.time)))
      }))
      .sort((a, b) => DAY_ORDER.indexOf(a.day) - DAY_ORDER.indexOf(b.day));
  }, [studentClassSlots, studentOfferings, user?.role]);

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

  const internshipSummary = useMemo(() => {
    if (!internshipStatus) {
      return { label: 'No active session', detail: 'Clock in to start internship attendance.' };
    }
    const status = internshipStatus.status || 'unknown';
    const inAt = internshipStatus.clock_in_at ? new Date(internshipStatus.clock_in_at).toLocaleString() : '-';
    const outAt = internshipStatus.clock_out_at ? new Date(internshipStatus.clock_out_at).toLocaleString() : '-';
    if (status === 'active') {
      return { label: 'Active session', detail: `Started: ${inAt}` };
    }
    if (status === 'auto_closed') {
      return { label: 'Auto-closed after 9h', detail: `Start: ${inAt} | Auto logout: ${outAt}` };
    }
    return { label: 'Closed session', detail: `Start: ${inAt} | End: ${outAt}` };
  }, [internshipStatus]);

  const chartChrome = useMemo(
    () => ({
      grid: isDark ? 'rgba(148,163,184,0.14)' : 'rgba(148,163,184,0.28)',
      axis: isDark ? '#94a3b8' : '#64748b',
      tooltipBg: isDark ? 'rgba(15,23,42,0.96)' : 'rgba(255,255,255,0.98)',
      tooltipBorder: isDark ? 'rgba(51,65,85,0.95)' : 'rgba(203,213,225,0.95)',
      tooltipText: isDark ? '#e2e8f0' : '#0f172a'
    }),
    [isDark]
  );

  const showInternshipCard = user?.role === 'student' && (hasInternshipEligibilityHint || internshipStatus !== null);

  if (user?.role === 'student') {
    return (
      <div className="space-y-5 page-fade">
        <div className="rounded-3xl border border-slate-200 bg-gradient-to-r from-sky-50 to-indigo-50 px-5 py-4 dark:border-slate-800 dark:from-slate-900 dark:to-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Student Workspace</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">Welcome back, {user?.full_name?.split(' ')[0] || 'Student'}</h1>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Track submissions, notices, and evaluations in one place.</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900">
                  <span className="text-slate-500">Department</span>
                  <span className="ml-2 font-semibold text-slate-800 dark:text-slate-100">{studentIdentity.department}</span>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900">
                  <span className="text-slate-500">Academic Track</span>
                  <span className="ml-2 font-semibold text-slate-800 dark:text-slate-100">{studentIdentity.academicTrack}</span>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900">
                  <span className="text-slate-500">Enrollment</span>
                  <span className="ml-2 font-semibold text-slate-800 dark:text-slate-100">{studentIdentity.enrollment}</span>
                </div>
              </div>
            </div>
            <Link to="/communication/announcements" className="btn-secondary relative self-start md:self-center">
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

        {urgentNotices.length > 0 ? (
          <Card>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Urgent Notices</h2>
              <Link to="/communication/announcements" className="text-xs font-semibold text-brand-700 dark:text-brand-300">View all</Link>
            </div>
            <div className="space-y-2">
              {urgentNotices.slice(0, 2).map((notice) => (
                <div key={notice.id} className="rounded-xl border border-rose-200 bg-rose-50 p-3 dark:border-rose-900/40 dark:bg-rose-950/25">
                  <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">{notice.title}</p>
                  <p className="mt-1 text-sm text-rose-700/90 dark:text-rose-200">{notice.message}</p>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-2">
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
                  <p className="text-xs text-slate-500">{session.teacher}</p>
                  <p className="text-xs text-slate-500">{session.room} | {session.type}{session.group ? ` | ${session.group}` : ''}</p>
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

          <Card>
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

        {showInternshipCard ? (
          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Internship Attendance</h2>
              <span className="text-xs text-slate-500">{internshipSummary.label}</span>
            </div>
            <p className="text-sm text-slate-500">{internshipSummary.detail}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                className="btn-primary"
                onClick={() => handleInternshipAction('clock_in')}
                disabled={internshipBusy || internshipStatus?.status === 'active'}
              >
                {internshipBusy ? 'Working...' : 'Clock In'}
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleInternshipAction('clock_out')}
                disabled={internshipBusy || internshipStatus?.status !== 'active'}
              >
                {internshipBusy ? 'Working...' : 'Clock Out'}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">Active sessions auto-close after 9 hours.</p>
          </Card>
        ) : null}

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
                <CartesianGrid stroke={chartChrome.grid} strokeDasharray="3 3" />
                <XAxis
                  dataKey="month"
                  tick={{ fill: chartChrome.axis, fontSize: 12 }}
                  axisLine={{ stroke: chartChrome.grid }}
                  tickLine={{ stroke: chartChrome.grid }}
                />
                <Tooltip
                  cursor={{ stroke: chartChrome.grid, strokeWidth: 1 }}
                  contentStyle={{
                    background: chartChrome.tooltipBg,
                    borderColor: chartChrome.tooltipBorder,
                    borderRadius: '1rem',
                    color: chartChrome.tooltipText
                  }}
                  labelStyle={{ color: chartChrome.tooltipText, fontWeight: 600 }}
                  itemStyle={{ color: chartChrome.tooltipText }}
                />
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
