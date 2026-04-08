import { memo } from 'react';
import { Link } from 'react-router-dom';
import PriorityBadge from './PriorityBadge';

function FeedCard({ item }) {
  return (
    <article
      className={`rounded-2xl border bg-white p-4 transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 ${
        item.isUnread
          ? 'border-brand-200 shadow-[0_0_0_1px_rgba(14,165,233,0.08)] dark:border-brand-800/60'
          : 'border-slate-200'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm text-slate-700 dark:text-slate-200">
            <span className="font-semibold">{item.actor}</span> {item.action}
          </p>
          <p className="text-xs text-slate-500">{item.targetAudience}</p>
          {item.meta ? <p className="text-xs text-slate-500">{item.meta}</p> : null}
          <p className="text-xs text-slate-400">{item.createdAt ? new Date(item.createdAt).toLocaleString() : '-'}</p>
        </div>

        <div className="flex items-center gap-2">
          {item.isUnread ? (
            <span className="rounded-md border border-brand-200 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-brand-700 dark:border-brand-800 dark:text-brand-300">
              Unread
            </span>
          ) : null}
          <span className="rounded-md border border-slate-200 px-2 py-1 text-[11px] uppercase tracking-wide text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {item.context}
          </span>
          {item.priority ? <PriorityBadge priority={item.priority} /> : null}
        </div>
      </div>

      {item.actionLink ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to={item.actionLink.to} className="btn-secondary">
            {item.actionLink.label}
          </Link>
        </div>
      ) : null}
    </article>
  );
}

export default memo(FeedCard);
