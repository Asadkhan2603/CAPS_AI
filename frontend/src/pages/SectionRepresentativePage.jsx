import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BookOpenCheck, CheckCircle2, Clock, Mail, Phone, RefreshCw, Shield, Users } from 'lucide-react';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { getSectionRepresentativeDashboard } from '../services/sectionsApi';

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function EmptyPanel({ title, description }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400">
      <p className="font-semibold text-slate-700 dark:text-slate-200">{title}</p>
      <p className="mt-1">{description}</p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4" data-testid="cr-dashboard-loading">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="h-24 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="h-44 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800" />
        <div className="h-44 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800" />
      </div>
    </div>
  );
}

function seatLabel(value) {
  return String(value || '').replace('_', '-').toUpperCase();
}

function SectionHeading({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 rounded-2xl bg-brand-50 p-2 text-brand-700 dark:bg-brand-950/40 dark:text-brand-200">
          <Icon size={18} />
        </span>
        <div>
          <h2 className="text-lg font-semibold text-slate-950 dark:text-slate-50">{title}</h2>
          {description ? <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p> : null}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, description, icon: Icon, tone = 'slate' }) {
  const tones = {
    brand: 'border-brand-200 bg-brand-50 text-brand-700 dark:border-brand-900/60 dark:bg-brand-950/30 dark:text-brand-200',
    amber: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200',
    slate: 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200'
  };
  return (
    <div className={`rounded-3xl border px-4 py-4 shadow-sm ${tones[tone] || tones.slate}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-80">{label}</p>
        {Icon ? (
          <span className="rounded-full bg-white/70 p-2 shadow-sm dark:bg-slate-950/40">
            <Icon size={16} />
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-slate-50">{value}</p>
      {description ? <p className="mt-1 text-xs opacity-80">{description}</p> : null}
    </div>
  );
}

function ProgressBar({ value }) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
      <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${safeValue}%` }} />
    </div>
  );
}

export default function SectionRepresentativePage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const representativeScope = (user?.role_scope || {}).class_representative || {};
  const sectionId = representativeScope.class_id || '';
  const seat = representativeScope.seat || 'cr_1';

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const attendanceSummary = dashboard?.attendance_summary || {};
  const attendanceRiskStudents = Array.isArray(dashboard?.attendance_risk_students) ? dashboard.attendance_risk_students : [];
  const assignments = Array.isArray(dashboard?.assignments) ? dashboard.assignments : [];
  const authorityContacts = Array.isArray(dashboard?.authority_contacts) ? dashboard.authority_contacts : [];
  const generatedAt = dashboard?.generated_at ? formatDate(dashboard.generated_at) : null;
  const totalStudents = attendanceSummary.total_students ?? 0;
  const riskCount = attendanceSummary.shortage_risk_count ?? attendanceRiskStudents.length ?? 0;
  const missingSubmissionCount = assignments.reduce(
    (total, assignment) => total + Number(assignment.missing_submission_count ?? assignment.missing_students?.length ?? 0),
    0
  );
  const reachableContacts = authorityContacts.filter((contact) => contact.email || contact.phone).length;
  const contactCoverage = authorityContacts.length ? `${reachableContacts}/${authorityContacts.length}` : '0/0';
  const sortedAttendanceRiskStudents = useMemo(
    () => [...attendanceRiskStudents].sort((first, second) => Number(first.attendance_percent ?? 100) - Number(second.attendance_percent ?? 100)),
    [attendanceRiskStudents]
  );

  async function loadDashboard() {
    if (!sectionId) {
      setDashboard(null);
      setError('Your account is not assigned to a CR section yet.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await getSectionRepresentativeDashboard(sectionId);
      setDashboard(data || null);
    } catch (err) {
      const message = err?.response?.data?.detail || 'Failed to load CR workspace';
      setError(String(message));
      pushToast({ title: 'Load failed', description: String(message), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, [sectionId]);

  const metrics = useMemo(
    () => [
      { label: 'Seat', value: seatLabel(seat), description: 'Section governance seat', icon: Shield, tone: 'brand' },
      { label: 'Students', value: totalStudents, description: 'Tracked in this section', icon: Users, tone: 'slate' },
      { label: 'Attendance Risk', value: riskCount, description: 'Students needing follow-up', icon: AlertTriangle, tone: riskCount ? 'amber' : 'emerald' },
      { label: 'Submission Gaps', value: missingSubmissionCount, description: 'Pending assignment submissions', icon: BookOpenCheck, tone: missingSubmissionCount ? 'amber' : 'emerald' },
    ],
    [missingSubmissionCount, riskCount, seat, totalStudents]
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="overflow-hidden border-brand-100 bg-gradient-to-br from-white via-brand-50/70 to-slate-50 shadow-sm dark:border-brand-950/40 dark:from-slate-950 dark:via-slate-900 dark:to-brand-950/20">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">Class Representative</p>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200">
                Read-only access
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950 dark:text-slate-50">CR Workspace</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600 dark:text-slate-300">
              View section attendance risk, assignment submission gaps, and escalation contacts for your assigned section.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full bg-brand-50 px-3 py-1 text-brand-700 dark:bg-brand-950/40 dark:text-brand-200">
                Section: {dashboard?.section_name || sectionId || 'Not assigned'}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                Seat: {String(seat || '').replace('_', '-').toUpperCase()}
              </span>
              {generatedAt ? (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  Updated: {generatedAt}
                </span>
              ) : null}
              <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                Contact coverage: {contactCoverage}
              </span>
            </div>
          </div>
          <button type="button" className="btn-secondary" onClick={() => void loadDashboard()} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {loading && !dashboard ? <LoadingSkeleton /> : null}

        {!loading || dashboard ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map((item) => (
              <MetricCard key={item.label} {...item} />
            ))}
          </div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
            {error}
          </div>
        ) : null}
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="space-y-4">
          <SectionHeading
            icon={Users}
            title="Attendance Risk"
            description="Named students who may need reminder, mentoring, or escalation support."
          />
          {!attendanceRiskStudents.length ? (
            <EmptyPanel
              title="No attendance risk right now"
              description="Students with shortage risk will appear here when attendance records cross the threshold."
            />
          ) : (
            <div className="space-y-3">
              {sortedAttendanceRiskStudents.map((student) => {
                const attendancePercent = Number(student.attendance_percent ?? 0);
                const critical = attendancePercent < 65;
                return (
                <div key={student.student_id} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{student.student_name}</p>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${critical ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-200' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200'}`}>
                      {attendancePercent}% attendance
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Roll No: {student.roll_number || '-'} | Marked Slots: {student.total_marked_slots ?? 0} | Absent: {student.absent_slots ?? 0}
                  </p>
                  <ProgressBar value={attendancePercent} />
                </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="space-y-4">
          <SectionHeading
            icon={Shield}
            title="Authority Contacts"
            description="Read-only escalation directory for class coordination and higher authority support."
          />
          {!authorityContacts.length ? (
            <EmptyPanel
              title="No authority contacts found"
              description="Ask an admin to verify coordinator, year-head, HOD, dean, or fallback authority records."
            />
          ) : (
            <div className="space-y-3">
              {authorityContacts.map((contact, index) => (
                <div key={`${contact.label}-${contact.user_id || index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{contact.label}</p>
                      <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">{contact.full_name || '-'}</p>
                      <p className="mt-1 text-xs text-slate-500">{contact.role || '-'}</p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${contact.email || contact.phone ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                      {contact.email || contact.phone ? 'Reachable' : 'Needs data'}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    {contact.email ? (
                      <a className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-1 text-slate-700 hover:border-brand-300 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200" href={`mailto:${contact.email}`}>
                        <Mail size={12} />
                        {contact.email}
                      </a>
                    ) : (
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-500 dark:bg-slate-800">No email available</span>
                    )}
                    {contact.phone ? (
                      <a className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-1 text-slate-700 hover:border-brand-300 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200" href={`tel:${contact.phone}`}>
                        <Phone size={12} />
                        {contact.phone}
                      </a>
                    ) : (
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-500 dark:bg-slate-800">No phone available</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <SectionHeading
            icon={BookOpenCheck}
            title="Assignment Submission Gaps"
            description="Open assignments with pending student submissions for this section."
          />
        </div>
        {!assignments.length ? (
          <EmptyPanel
            title="No open submission gaps"
            description="Open assignments with missing student submissions will appear here."
          />
        ) : (
          <div className="space-y-4">
            {assignments.map((assignment) => (
              <div key={assignment.assignment_id} className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm dark:border-slate-700 dark:bg-slate-950/40">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{assignment.title}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Due: {formatDate(assignment.due_date)} | Missing: {assignment.missing_submission_count}/{assignment.total_students}
                    </p>
                  </div>
                  <span className="rounded-full bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700 dark:bg-rose-900/30 dark:text-rose-200">
                    {assignment.status || 'open'}
                  </span>
                </div>
                {!assignment.missing_students?.length ? (
                  <p className="mt-3 text-sm text-emerald-600 dark:text-emerald-300">All tracked students have submitted this assignment.</p>
                ) : (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {assignment.missing_students.map((student) => (
                      <span key={`${assignment.assignment_id}-${student.student_id}`} className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300">
                        {student.student_name} {student.roll_number ? `(${student.roll_number})` : ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="grid gap-3 border-emerald-100 bg-emerald-50/60 text-sm dark:border-emerald-950/40 dark:bg-emerald-950/20 md:grid-cols-3">
        <div className="flex items-start gap-2">
          <CheckCircle2 size={18} className="mt-0.5 text-emerald-600" />
          <div>
            <p className="font-semibold text-emerald-900 dark:text-emerald-100">Can view section signals</p>
            <p className="mt-1 text-xs text-emerald-800/80 dark:text-emerald-200/80">Attendance risk, submission gaps, and authority contacts are available for follow-up.</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Shield size={18} className="mt-0.5 text-emerald-600" />
          <div>
            <p className="font-semibold text-emerald-900 dark:text-emerald-100">Cannot modify records</p>
            <p className="mt-1 text-xs text-emerald-800/80 dark:text-emerald-200/80">CR access stays read-only: no attendance marking, grading, status, or discipline mutation.</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Clock size={18} className="mt-0.5 text-emerald-600" />
          <div>
            <p className="font-semibold text-emerald-900 dark:text-emerald-100">Use contacts for escalation</p>
            <p className="mt-1 text-xs text-emerald-800/80 dark:text-emerald-200/80">Reach out to the listed coordinator, year head, HOD, dean, or fallback authority when needed.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
