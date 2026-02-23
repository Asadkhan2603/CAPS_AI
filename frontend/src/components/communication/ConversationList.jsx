const MOCK_THREADS = [
  { id: 't1', name: 'CSE 4A - Announcements', preview: 'Midsem review at 2 PM', unread: 2 },
  { id: 't2', name: 'DS Faculty Group', preview: 'Syllabus update draft shared', unread: 0 },
  { id: 't3', name: 'Student Support', preview: 'Need clarification on assignment', unread: 1 }
];

export default function ConversationList({ activeId, onSelect }) {
  return (
    <aside className="w-full rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900 lg:w-80">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Conversations</h3>
      <div className="space-y-2">
        {MOCK_THREADS.map((thread) => (
          <button
            key={thread.id}
            type="button"
            onClick={() => onSelect(thread.id)}
            className={`w-full rounded-xl border px-3 py-2 text-left transition ${
              activeId === thread.id
                ? 'border-slate-900 bg-slate-50 dark:border-slate-200 dark:bg-slate-800'
                : 'border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800'
            }`}
          >
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{thread.name}</p>
            <p className="truncate text-xs text-slate-500">{thread.preview}</p>
            {thread.unread > 0 ? (
              <span className="mt-1 inline-flex rounded-full bg-brand-600 px-2 py-0.5 text-[11px] text-white">{thread.unread}</span>
            ) : null}
          </button>
        ))}
      </div>
    </aside>
  );
}
