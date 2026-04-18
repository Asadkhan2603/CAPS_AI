import React from 'react';
import { ArrowLeft, Home, LockKeyhole } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getWorkspaceHomeItemPath } from '../../config/navigationGroups';

function titleize(value) {
  if (!value) {
    return 'Not assigned';
  }
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatList(values = []) {
  if (!values.length) {
    return 'Any';
  }
  return values.map((value) => titleize(value)).join(', ');
}

function normalizePath(pathname) {
  if (!pathname) {
    return '/';
  }
  return pathname.replace(/\/+$/, '') || '/';
}

export default function AccessDeniedState({
  user,
  pathname,
  allowedRoles = [],
  requiredTeacherExtensions = [],
  requiredStudentExtensions = [],
  requiredAdminTypes = []
}) {
  const homePath = getWorkspaceHomeItemPath(user);
  const currentRoleLabel = titleize(user?.role);
  const currentAdminTypeLabel = user?.role === 'admin' ? titleize(user?.admin_type || 'admin') : 'Not applicable';
  const currentTeacherExtensions = user?.role === 'teacher'
    ? ((user?.extended_roles || []).length ? formatList(user.extended_roles) : 'None')
    : 'Not applicable';
  const currentStudentExtensions = user?.role === 'student'
    ? ((user?.extended_roles || []).length ? formatList(user.extended_roles) : 'None')
    : 'Not applicable';

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 rounded-3xl border border-slate-200 bg-white/95 p-6 shadow-soft dark:border-slate-800 dark:bg-slate-950/70 sm:p-8">
      <div className="flex items-start gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
          <LockKeyhole size={24} />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-600 dark:text-amber-300">
            Access Control
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">
            You do not have access to this page
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            This route exists, but your current role or extension does not include it. If this looks incorrect,
            the permission contract for this workflow should be reviewed instead of silently redirecting you away.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50/90 p-4 dark:border-slate-800 dark:bg-slate-900/80">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
          Requested Route
        </p>
        <p className="mt-2 break-all rounded-xl bg-slate-900 px-3 py-2 font-mono text-sm text-white dark:bg-slate-950">
          {normalizePath(pathname)}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
            Your Access
          </p>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">Role: {currentRoleLabel}</p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">Admin Type: {currentAdminTypeLabel}</p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
            Teacher Extensions: {currentTeacherExtensions}
          </p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
            Student Extensions: {currentStudentExtensions}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
            Required Access
          </p>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">Roles: {formatList(allowedRoles)}</p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
            Admin Types: {formatList(requiredAdminTypes)}
          </p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
            Teacher Extensions: {formatList(requiredTeacherExtensions)}
          </p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
            Student Extensions: {formatList(requiredStudentExtensions)}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link to={homePath} className="btn-primary">
          <Home size={16} /> Go To Home
        </Link>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            if (typeof window !== 'undefined' && window.history.length > 1) {
              window.history.back();
              return;
            }
            window.location.assign(homePath);
          }}
        >
          <ArrowLeft size={16} /> Go Back
        </button>
      </div>
    </div>
  );
}
