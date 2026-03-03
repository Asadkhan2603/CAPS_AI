import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import Card from './Card';
import FormInput from './FormInput';
import Table from './Table';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';

export default function EntityManager({
  title,
  endpoint,
  listEndpoint,
  createEndpoint,
  deleteEndpoint,
  filters = [],
  createFields = [],
  columns = [],
  pageSizeOptions = [5, 10, 20],
  createTransform,
  enableDelete = false,
  hideCreate = false,
  rowActions = []
}) {
  const listPath = (listEndpoint || endpoint).replace(/\/+$/, '');
  const createPath = (createEndpoint || endpoint).replace(/\/+$/, '');
  const deletePath = (deleteEndpoint || listEndpoint || endpoint).replace(/\/+$/, '');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(pageSizeOptions[1] ?? 10);
  const [error, setError] = useState('');
  const { pushToast } = useToast();

  const initialFilterState = useMemo(
    () =>
      filters.reduce((acc, item) => {
        if (item.type === 'switch') {
          acc[item.name] = item.defaultValue ?? null;
        } else {
          acc[item.name] = item.defaultValue ?? '';
        }
        return acc;
      }, {}),
    [filters]
  );

  const initialCreateState = useMemo(
    () =>
      createFields.reduce((acc, item) => {
        acc[item.name] = item.defaultValue ?? (item.type === 'number' ? 0 : '');
        return acc;
      }, {}),
    [createFields]
  );

  const [filterValues, setFilterValues] = useState(initialFilterState);
  const [createValues, setCreateValues] = useState(initialCreateState);

  useEffect(() => {
    setFilterValues(initialFilterState);
  }, [initialFilterState]);

  useEffect(() => {
    setCreateValues(initialCreateState);
  }, [initialCreateState]);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const params = Object.entries(filterValues).reduce((acc, [key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          acc[key] = value;
        }
        return acc;
      }, {});
      params.skip = skip;
      params.limit = limit;

      const response = await apiClient.get(listPath, { params });
      setRows(response.data);
    } catch (err) {
      const message = formatApiError(err, `Failed to load ${title.toLowerCase()}`);
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [skip, limit]);

  function onFilterChange(name, value) {
    setFilterValues((prev) => ({ ...prev, [name]: value }));
  }

  function onCreateChange(name, value) {
    setCreateValues((prev) => ({ ...prev, [name]: value }));
  }

  async function onCreate(event) {
    event.preventDefault();
    setError('');
    try {
      let payload = { ...createValues };
      payload = createFields.reduce((acc, field) => {
        if (field.nullable && acc[field.name] === '') {
          acc[field.name] = null;
        }
        if (field.type === 'number') {
          acc[field.name] = Number(acc[field.name]);
        }
        if (field.type === 'datetime' && acc[field.name]) {
          acc[field.name] = new Date(acc[field.name]).toISOString();
        }
        return acc;
      }, payload);

      if (createTransform) {
        payload = createTransform(payload);
      }

      await apiClient.post(createPath, payload);
      setCreateValues(initialCreateState);
      pushToast({ title: 'Saved', description: `${title.slice(0, -1)} created successfully.`, variant: 'success' });
      await loadData();
    } catch (err) {
      const message = formatApiError(err, `Failed to create ${title.toLowerCase()}`);
      setError(message);
      pushToast({ title: 'Create failed', description: message, variant: 'error' });
    }
  }

  async function onDelete(row) {
    try {
      await apiClient.delete(`${deletePath}/${row.id}`);
      pushToast({ title: 'Deleted', description: `${title.slice(0, -1)} removed.`, variant: 'success' });
      await loadData();
    } catch (err) {
      const message = formatApiError(err, `Failed to delete ${title.toLowerCase()}`);
      pushToast({ title: 'Delete failed', description: message, variant: 'error' });
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold">{title}</h1>
            <div className="flex items-center gap-2">
              <button className="btn-secondary" onClick={() => { setSkip(0); loadData(); }}>
                Refresh
              </button>
            </div>
          </div>

          {filters.length ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {filters.map((field) => (
                field.type === 'switch' ? (
                  <label key={field.name} className="block space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{field.label}</span>
                    <button
                      type="button"
                      className="inline-flex h-11 min-w-[8.5rem] items-center justify-center rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                      onClick={() => {
                        const current = filterValues[field.name];
                        const next = current === null ? true : current === true ? false : null;
                        onFilterChange(field.name, next);
                      }}
                    >
                      {filterValues[field.name] === null ? 'Any' : filterValues[field.name] ? 'On' : 'Off'}
                    </button>
                  </label>
                ) : field.type === 'select' ? (
                  <FormInput
                    key={field.name}
                    as="select"
                    label={field.label}
                    value={filterValues[field.name]}
                    onChange={(e) => onFilterChange(field.name, e.target.value)}
                  >
                    <option value="">{field.placeholder || `All ${field.label}`}</option>
                    {(field.options || []).map((option) => (
                      <option key={`${field.name}-${option.value}`} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </FormInput>
                ) : (
                  <FormInput
                    key={field.name}
                    label={field.label}
                    type={field.type === 'datetime' ? 'datetime-local' : (field.type || 'text')}
                    value={filterValues[field.name]}
                    placeholder={field.placeholder}
                    onChange={(e) => onFilterChange(field.name, e.target.value)}
                  />
                )
              ))}
            </div>
          ) : null}
        </Card>
      </motion.div>

      {!hideCreate ? (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 }}>
          <Card>
            <h2 className="mb-3 text-lg font-semibold">Create {title.slice(0, -1)}</h2>
            <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {createFields.map((field) => (
                field.type === 'switch' ? (
                  <label key={field.name} className="block space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{field.label}</span>
                    <div className="flex h-11 items-center">
                      <label className="inline-flex cursor-pointer items-center gap-2">
                        <input
                          type="checkbox"
                          className="peer sr-only"
                          checked={Boolean(createValues[field.name])}
                          onChange={(e) => onCreateChange(field.name, e.target.checked)}
                        />
                        <span className="relative h-6 w-11 rounded-full bg-slate-300 transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-transform after:content-[''] peer-checked:bg-brand-500 peer-checked:after:translate-x-5 dark:bg-slate-700" />
                        <span className="text-xs text-slate-600 dark:text-slate-300">
                          {createValues[field.name] ? 'Enabled' : 'Disabled'}
                        </span>
                      </label>
                    </div>
                  </label>
                ) : field.type === 'select' ? (
                  <FormInput
                    key={field.name}
                    as="select"
                    label={field.label}
                    required={field.required}
                    value={createValues[field.name]}
                    onChange={(e) => onCreateChange(field.name, e.target.value)}
                  >
                    <option value="">{field.placeholder || `Select ${field.label}`}</option>
                    {(field.options || []).map((option) => (
                      <option key={`${field.name}-${option.value}`} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </FormInput>
                ) : (
                  <FormInput
                    key={field.name}
                    label={field.label}
                    type={field.type === 'datetime' ? 'datetime-local' : (field.type || 'text')}
                    min={field.min}
                    max={field.max}
                    required={field.required}
                    value={createValues[field.name]}
                    placeholder={field.placeholder}
                    onChange={(e) => onCreateChange(field.name, e.target.value)}
                  />
                )
              ))}
              <div className="flex items-end">
                <button type="submit" className="btn-primary w-full">Create</button>
              </div>
            </form>
          </Card>
        </motion.div>
      ) : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{title} List</h2>
            <div className="flex items-center gap-2">
              <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>Prev</button>
              <span className="text-xs text-slate-500">skip: {skip}</span>
              <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>Next</button>
              <select className="input w-24" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </div>
          </div>

          {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Table
            columns={columns}
            data={rows}
            onDelete={enableDelete ? onDelete : undefined}
            rowActions={rowActions.map((action) => ({
              ...action,
              onClick: async (row) => {
                try {
                  await action.onClick(row, { reload: loadData, pushToast });
                } catch (err) {
                  const message = formatApiError(err, 'Action failed');
                  pushToast({ title: 'Action failed', description: message, variant: 'error' });
                }
              }
            }))}
          />
        </Card>
      </motion.div>
    </div>
  );
}
