import {
  Bell,
  BookOpen,
  CircleHelp,
  Headset,
  Link2,
  MessageSquare,
  ShieldCheck,
  UserRoundCog
} from 'lucide-react';
import { Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';

function getPrimaryLinks(user) {
  if (user?.role === 'admin') {
    return [
      { to: '/admin/onboarding', label: 'Open Onboarding', icon: BookOpen },
      { to: '/notifications', label: 'Review Notifications', icon: Bell },
      { to: '/users', label: 'Open User Administration', icon: UserRoundCog }
    ];
  }

  if (user?.role === 'teacher') {
    return [
      { to: '/sections', label: 'Open Sections', icon: BookOpen },
      { to: '/notifications', label: 'Review Notifications', icon: Bell },
      { to: '/profile', label: 'Update Profile', icon: UserRoundCog }
    ];
  }

  return [
    { to: '/notifications', label: 'Review Notifications', icon: Bell },
    { to: '/history', label: 'Open Activity History', icon: BookOpen },
    { to: '/profile', label: 'Update Profile', icon: UserRoundCog }
  ];
}

function getSupportChecks(user) {
  if (user?.role === 'admin') {
    return [
      'If a workflow exists but opens an access-denied state, verify your admin subtype and governance policy first.',
      'Use Control Center for admin-only workflows, then move into Students & Academics, Administration, or System & Compliance for execution.',
      'Check Notifications before escalating so recent system or governance warnings are not missed.'
    ];
  }

  if (user?.role === 'teacher') {
    return [
      'If you cannot open a route, check whether the workflow requires `year_head` or `class_coordinator` extensions.',
      'Use Notifications before escalation so timetable, submission, or attendance changes are reviewed first.',
      'Keep your profile current so role-based handoffs and support follow-ups stay accurate.'
    ];
  }

  return [
    'Check Notifications first for assignment, evaluation, or event updates before escalating.',
    'Use Activity History to confirm whether a submission, registration, or alert was already recorded.',
    'Keep your profile details current so support follow-up stays accurate.'
  ];
}

export default function HelpSupportPage() {
  const { user } = useAuth();
  const primaryLinks = getPrimaryLinks(user);
  const supportChecks = getSupportChecks(user);

  return (
    <div className="space-y-5 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl space-y-2">
            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-brand-700 dark:text-brand-300">
              <CircleHelp size={14} /> Help & Support
            </p>
            <h1 className="text-2xl font-semibold text-slate-950 dark:text-white">Truthful support path for this workspace</h1>
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              This page is the real support destination for the shell. It explains where to self-serve first,
              how to validate access problems, and which live routes to use before escalating.
            </p>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200">
            <p className="font-semibold">Current workspace role</p>
            <p className="mt-1 capitalize">{String(user?.admin_type || user?.role || 'member').replace(/_/g, ' ')}</p>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Start Here</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Use these live routes before assuming something is broken.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {primaryLinks.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm font-semibold text-slate-800 transition hover:border-brand-300 hover:bg-white dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-100 dark:hover:border-brand-700"
                >
                  <span className="flex items-center gap-2">
                    <Icon size={16} />
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/40">
            <p className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
              <ShieldCheck size={16} /> Access checks before escalation
            </p>
            <div className="mt-3 space-y-2">
              {supportChecks.map((item) => (
                <p key={item} className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="space-y-3">
            <h2 className="inline-flex items-center gap-2 text-lg font-semibold text-slate-950 dark:text-white">
              <Headset size={18} /> When To Escalate
            </h2>
            <div className="space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              <p>Escalate when a real route stays unavailable after checking role, admin subtype, or teacher extensions.</p>
              <p>Escalate when saved work is missing from Notifications, History, or the target workspace after refresh.</p>
              <p>Escalate when a control appears truthful but lands on the wrong destination or exposes stale labels.</p>
            </div>
          </Card>

          <Card className="space-y-3">
            <h2 className="inline-flex items-center gap-2 text-lg font-semibold text-slate-950 dark:text-white">
              <MessageSquare size={18} /> Support Handoff Template
            </h2>
            <div className="rounded-2xl bg-slate-950 px-4 py-4 font-mono text-sm text-slate-100 dark:bg-black">
              <p>Route: /example</p>
              <p>Role: {user?.role || 'unknown'}</p>
              <p>Admin type / extensions: {user?.admin_type || (user?.extended_roles || []).join(', ') || 'n/a'}</p>
              <p>Expected result: open the target workflow</p>
              <p>Actual result: blocked, missing data, or wrong destination</p>
            </div>
          </Card>

          <Card className="space-y-3">
            <h2 className="inline-flex items-center gap-2 text-lg font-semibold text-slate-950 dark:text-white">
              <Link2 size={18} /> Useful Live Routes
            </h2>
            <div className="grid gap-2 text-sm">
              <Link className="text-brand-700 hover:underline dark:text-brand-300" to="/notifications">/notifications</Link>
              <Link className="text-brand-700 hover:underline dark:text-brand-300" to="/history">/history</Link>
              <Link className="text-brand-700 hover:underline dark:text-brand-300" to="/profile">/profile</Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
