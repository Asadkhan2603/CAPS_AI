import React from 'react';
import { cn } from '../../utils/cn';

export default function PageLoader({ label = 'Loading...', compact = false, className = '' }) {
  return (
    <div className={cn('flex items-center justify-center', compact ? 'min-h-[7rem]' : 'min-h-[40vh]', className)}>
      <div className={cn('flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft dark:border-slate-800 dark:bg-slate-900', compact ? 'w-full justify-center' : '')}>
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        <span className="text-sm text-slate-600 dark:text-slate-300">{label}</span>
      </div>
    </div>
  );
}
