import { ArrowRight, Layers3 } from 'lucide-react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { useMemo } from 'react';
import { getVisibleNavigationGroups, getWorkspaceItemPath } from '../config/navigationGroups';
import { useAuth } from '../hooks/useAuth';

function describeGroup(groupLabel, itemLabel) {
  return `Open ${itemLabel} inside ${groupLabel}.`;
}

export default function NavigationGroupPage() {
  const { groupKey = '' } = useParams();
  const { user } = useAuth();
  const visibleGroups = useMemo(() => getVisibleNavigationGroups(user), [user]);
  const activeGroup = visibleGroups.find((group) => group.key === groupKey) || null;

  if (!visibleGroups.length) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-8 dark:border-slate-800 dark:bg-slate-900/70">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">No Modules Available</h1>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          There are no visible module groups for your current role.
        </p>
      </div>
    );
  }

  if (!activeGroup) {
    return <Navigate to={`/workspace/${visibleGroups[0].key}`} replace />;
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-[1.75rem] border border-slate-200/80 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.12),transparent_35%),radial-gradient(circle_at_top_right,rgba(99,102,241,0.16),transparent_40%),white] p-5 shadow-sm dark:border-slate-800 dark:bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_35%),radial-gradient(circle_at_top_right,rgba(99,102,241,0.22),transparent_40%),rgba(15,23,42,0.92)] lg:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-500">
              Module Workspace
            </p>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-white lg:text-3xl">
              {activeGroup.label}
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Choose a module from this workspace. Each tile opens the actual page for that area.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-right shadow-sm dark:border-slate-700 dark:bg-slate-900/70">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
              Available Modules
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">
              {activeGroup.items.length}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {activeGroup.items.map((item) => (
          <Link
            key={item.to}
            to={getWorkspaceItemPath(activeGroup.key, item.to)}
            className="group flex min-h-[9.5rem] flex-col justify-between rounded-[1.35rem] border border-slate-200 bg-white/90 p-4 transition hover:-translate-y-1 hover:border-brand-200 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900/80 dark:hover:border-brand-700"
          >
            <div className="space-y-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-200 dark:group-hover:bg-brand-900/50">
                {item.icon ? <item.icon size={20} /> : <Layers3 size={20} />}
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">{item.label}</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                  {activeGroup.label}
                </p>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between text-sm font-semibold text-brand-600 dark:text-brand-300">
              <span>Open module</span>
              <ArrowRight size={16} className="transition group-hover:translate-x-1" />
            </div>
          </Link>
        ))}
      </section>
    </div>
  );
}
