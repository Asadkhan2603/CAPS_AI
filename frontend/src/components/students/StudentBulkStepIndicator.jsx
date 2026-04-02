import { Check } from 'lucide-react';
import { cn } from '../../utils/cn';

export default function StudentBulkStepIndicator({ steps, currentStep = 1 }) {
  return (
    <div className="rounded-[1.2rem] border border-slate-200/80 bg-white/70 p-2.5 dark:border-slate-700/70 dark:bg-slate-900/70">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-0">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const status =
            stepNumber < currentStep ? 'complete' : stepNumber === currentStep ? 'current' : 'upcoming';

          return (
            <div key={step.title} className="flex min-w-0 flex-1 items-center gap-2">
              <div
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border text-xs font-semibold transition-all',
                  status === 'complete' && 'border-emerald-300 bg-emerald-500 text-white shadow-[0_12px_24px_-16px_rgba(16,185,129,0.7)]',
                  status === 'current' && 'border-brand-400 bg-gradient-to-br from-brand-500 to-indigo-600 text-white shadow-[0_12px_24px_-14px_rgba(79,70,229,0.7)]',
                  status === 'upcoming' && 'border-slate-200 bg-slate-50 text-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-500'
                )}
              >
                {status === 'complete' ? <Check size={15} /> : stepNumber}
              </div>

              <div className="min-w-0">
                <p
                  className={cn(
                    'truncate text-[13px] font-semibold',
                    status === 'current' ? 'text-slate-950 dark:text-white' : 'text-slate-700 dark:text-slate-200'
                  )}
                >
                  {step.title}
                </p>
                <p
                  className={cn(
                    'truncate text-[11px]',
                    status === 'current' ? 'text-brand-700 dark:text-brand-300' : 'text-slate-400 dark:text-slate-500'
                  )}
                >
                  {status === 'complete' ? 'Completed' : status === 'current' ? 'In progress' : 'Queued'}
                </p>
              </div>

              {index < steps.length - 1 ? (
                <div
                  className={cn(
                    'mx-2 hidden h-px flex-1 lg:block',
                    status === 'complete'
                      ? 'bg-gradient-to-r from-emerald-300 via-emerald-200 to-slate-200 dark:from-emerald-500/60 dark:via-slate-700 dark:to-slate-700'
                      : 'bg-gradient-to-r from-slate-200 via-slate-200 to-transparent dark:from-slate-700 dark:via-slate-700'
                  )}
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
