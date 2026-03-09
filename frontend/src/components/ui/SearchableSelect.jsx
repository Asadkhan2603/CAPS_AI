import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Search, X } from 'lucide-react';

function normalize(text) {
  return String(text || '')
    .trim()
    .toLowerCase();
}

export default function SearchableSelect({
  label,
  value,
  options = [],
  placeholder = 'Select option',
  allowEmpty = false,
  emptyLabel = 'All',
  required = false,
  onValueChange
}) {
  const containerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selectedOption = useMemo(
    () => options.find((option) => String(option.value) === String(value)),
    [options, value]
  );

  useEffect(() => {
    setQuery(selectedOption?.label || '');
  }, [selectedOption?.label]);

  useEffect(() => {
    function onPointerDown(event) {
      if (!containerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, []);

  const filteredOptions = useMemo(() => {
    const q = normalize(query);
    if (!q) return options;
    return options.filter((option) =>
      normalize(`${option.label} ${option.value}`).includes(q)
    );
  }, [options, query]);

  function selectValue(nextValue, nextLabel = '') {
    onValueChange?.(nextValue);
    setQuery(nextLabel);
    setOpen(false);
  }

  function onInputChange(nextQuery) {
    setQuery(nextQuery);
    if (!nextQuery && allowEmpty) {
      onValueChange?.('');
    }
    setOpen(true);
  }

  return (
    <label className="block space-y-1">
      {label ? (
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {label}
        </span>
      ) : null}

      <div className="relative" ref={containerRef}>
        <Search
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        />
        <input
          className="input !pl-9 !pr-16"
          value={query}
          placeholder={placeholder}
          required={required}
          onChange={(event) => onInputChange(event.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            window.setTimeout(() => {
              setOpen(false);
              if (selectedOption?.label) {
                setQuery(selectedOption.label);
                return;
              }
              if (!allowEmpty) {
                setQuery('');
              }
            }, 120);
          }}
        />
        <div className="absolute inset-y-0 right-2 flex items-center gap-1">
          {allowEmpty && value ? (
            <button
              type="button"
              className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              onClick={() => selectValue('', '')}
              title="Clear"
            >
              <X size={14} />
            </button>
          ) : null}
          <ChevronDown size={14} className={`text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>

        {open ? (
          <div className="absolute z-50 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-slate-200 bg-white p-1 shadow-soft dark:border-slate-700 dark:bg-slate-900">
            {allowEmpty ? (
              <button
                type="button"
                className={`w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800 ${
                  !value ? 'bg-slate-100 dark:bg-slate-800' : ''
                }`}
                onClick={() => selectValue('', '')}
              >
                {emptyLabel}
              </button>
            ) : null}

            {filteredOptions.length ? (
              filteredOptions.map((option) => (
                <button
                  type="button"
                  key={String(option.value)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800 ${
                    String(option.value) === String(value) ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200' : ''
                  }`}
                  onClick={() => selectValue(option.value, option.label)}
                >
                  {option.label}
                </button>
              ))
            ) : (
              <p className="px-3 py-2 text-sm text-slate-500">No matches found</p>
            )}
          </div>
        ) : null}
      </div>
    </label>
  );
}
