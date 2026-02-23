import { memo } from 'react';
import PriorityBadge from './PriorityBadge';

function FeedCard({ item }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm text-slate-700 dark:text-slate-200">
            <span className="font-semibold">{item.actor}</span> {item.action}
          </p>
          <p className="text-xs text-slate-500">{item.targetAudience}</p>
          <p className="text-xs text-slate-400">{item.createdAt ? new Date(item.createdAt).toLocaleString() : '-'}</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-md border border-slate-200 px-2 py-1 text-[11px] uppercase tracking-wide text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {item.context}
          </span>
          {item.priority ? <PriorityBadge priority={item.priority} /> : null}
        </div>
      </div>
    </article>
  );
}

export default memo(FeedCard);
