import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';

export default function AudienceSelector({ options, value, onChange, disabled = false }) {
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((item) => item.searchText.includes(q));
  }, [options, query]);

  const selected = useMemo(() => options.find((item) => item.key === value) || null, [options, value]);

  return (
    <div className="space-y-2">
      <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Audience</label>
      <div className="rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
        <label className="relative block">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Search audience (class, year, subject, college...)"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={disabled}
          />
        </label>

        <div className="mt-2 max-h-52 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-800">
          {filtered.length === 0 ? (
            <p className="px-3 py-4 text-sm text-slate-500">No audience found.</p>
          ) : (
            filtered.map((item) => (
              <button
                key={item.key}
                type="button"
                disabled={disabled}
                onClick={() => onChange(item)}
                className={`flex w-full items-center justify-between border-b border-slate-200 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800 ${
                  selected?.key === item.key ? 'bg-brand-50 dark:bg-brand-900/15' : ''
                }`}
              >
                <span className="text-sm text-slate-700 dark:text-slate-200">{item.label}</span>
                <span className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  {item.scope === 'class' ? 'section' : item.scope}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
