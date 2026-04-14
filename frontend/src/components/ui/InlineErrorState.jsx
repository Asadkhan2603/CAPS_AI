import React from 'react';
import { cn } from '../../utils/cn';

export default function InlineErrorState({
  title = 'Something went wrong',
  description = 'We could not load this section right now.',
  retryLabel = 'Retry',
  onRetry,
  className = '',
  compact = false,
}) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/70 dark:bg-rose-950/30 dark:text-rose-100',
        compact ? 'px-4 py-4' : 'px-5 py-5',
        className,
      )}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-sm text-rose-800 dark:text-rose-200">{description}</p>
        </div>
        {onRetry ? (
          <button type="button" className="btn-secondary w-fit" onClick={onRetry}>
            {retryLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}
