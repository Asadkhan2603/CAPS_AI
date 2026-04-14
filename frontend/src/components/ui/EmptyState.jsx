import React from 'react';
import { cn } from '../../utils/cn';

export default function EmptyState({
  title = 'No data',
  description = 'Nothing to show right now.',
  action = null,
  compact = false,
  className = '',
}) {
  return (
    <div className={cn('rounded-xl border border-dashed border-slate-300 bg-white text-center dark:border-slate-700 dark:bg-slate-900', compact ? 'p-4' : 'p-6', className)}>
      <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">{title}</h3>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
