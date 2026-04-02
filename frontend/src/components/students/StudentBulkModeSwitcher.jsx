import { ShieldCheck, UserPlus } from 'lucide-react';
import { cn } from '../../utils/cn';

const MODE_META = {
  create_students: {
    title: 'Create Students',
    description: 'Global records first, mapping later.',
    icon: UserPlus
  },
  map_existing: {
    title: 'Map Existing Students',
    description: 'Assign existing records into sections safely.',
    icon: ShieldCheck
  }
};

export default function StudentBulkModeSwitcher({ workflow, onChange, disabled = false }) {
  return (
    <div className="space-y-2.5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Workflow Mode</p>
        <p className="mt-1 text-sm text-slate-500">
          Choose whether this run creates global student records or maps existing students into a section.
        </p>
      </div>

      <div className="grid gap-2.5 lg:grid-cols-2">
        {Object.entries(MODE_META).map(([value, meta]) => {
          const Icon = meta.icon;
          const active = workflow === value;

          return (
            <button
              key={value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(value)}
              className={cn(
                'rounded-[1.05rem] border px-3 py-2.5 text-left transition-all',
                active
                  ? 'border-brand-400 bg-gradient-to-br from-brand-500 to-indigo-600 text-white shadow-[0_18px_36px_-26px_rgba(79,70,229,0.8)]'
                  : 'border-slate-200 bg-white/90 text-slate-700 hover:border-brand-200 hover:bg-brand-50/40 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-200'
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border',
                    active
                      ? 'border-white/30 bg-white/15 text-white'
                      : 'border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'
                  )}
                >
                  <Icon size={16} />
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">{meta.title}</p>
                    {active ? (
                      <span className="rounded-full border border-white/20 bg-white/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/80">
                        Active
                      </span>
                    ) : null}
                  </div>
                  <p className={cn('mt-0.5 text-[11px] leading-5', active ? 'text-white/85' : 'text-slate-500 dark:text-slate-400')}>
                    {meta.description}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
