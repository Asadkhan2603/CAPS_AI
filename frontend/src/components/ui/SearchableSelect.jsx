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
  loadOptions,
  placeholder = 'Select option',
  allowEmpty = false,
  emptyLabel = 'All',
  required = false,
  disabled = false,
  selectedLabel = '',
  onValueChange
}) {
  const containerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [asyncOptions, setAsyncOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const requestIdRef = useRef(0);

  const resolvedOptions = loadOptions ? asyncOptions : options;

  const selectedOption = useMemo(
    () => resolvedOptions.find((option) => String(option.value) === String(value)),
    [resolvedOptions, value]
  );

  useEffect(() => {
    setQuery(selectedOption?.label || selectedLabel || '');
  }, [selectedLabel, selectedOption?.label]);

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
    if (loadOptions) return resolvedOptions;
    if (!q) return resolvedOptions;
    return resolvedOptions.filter((option) =>
      normalize(`${option.label} ${option.value}`).includes(q)
    );
  }, [loadOptions, query, resolvedOptions]);

  useEffect(() => {
    if (!loadOptions || !open || disabled) return undefined;

    let cancelled = false;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);

    const timer = window.setTimeout(async () => {
      try {
        const nextOptions = await loadOptions(query);
        if (cancelled || requestId !== requestIdRef.current) return;
        setAsyncOptions(Array.isArray(nextOptions) ? nextOptions : []);
      } catch {
        if (!cancelled && requestId === requestIdRef.current) {
          setAsyncOptions([]);
        }
      } finally {
        if (!cancelled && requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    }, 180);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [disabled, loadOptions, open, query]);

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
    if (!disabled) {
      setOpen(true);
    }
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
          disabled={disabled}
          onChange={(event) => onInputChange(event.target.value)}
          onFocus={() => {
            if (!disabled) {
              setOpen(true);
            }
          }}
          onBlur={() => {
            window.setTimeout(() => {
              setOpen(false);
              if (selectedOption?.label) {
                setQuery(selectedOption.label);
                return;
              }
              if (selectedLabel) {
                setQuery(selectedLabel);
                return;
              }
              if (!allowEmpty) {
                setQuery('');
              }
            }, 120);
          }}
        />
        <div className="absolute inset-y-0 right-2 flex items-center gap-1">
          {allowEmpty && value && !disabled ? (
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

        {open && !disabled ? (
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

            {loading ? (
              <p className="px-3 py-2 text-sm text-slate-500">Loading...</p>
            ) : filteredOptions.length ? (
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
