import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import Card from './Card';
import FormInput from './FormInput';
import Table from './Table';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';

export default function EntityManager({
  title,
  endpoint,
  filters = [],
  createFields = [],
  columns = [],
  pageSizeOptions = [5, 10, 20],
  createTransform,
  enableDelete = false,
  hideCreate = false
}) {
  const normalizedEndpoint = endpoint.replace(/\/+$/, '');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(pageSizeOptions[1] ?? 10);
  const [error, setError] = useState('');
  const { pushToast } = useToast();

  const initialFilterState = useMemo(
    () =>
      filters.reduce((acc, item) => {
        acc[item.name] = item.defaultValue ?? '';
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

      const response = await apiClient.get(endpoint, { params });
      setRows(response.data);
    } catch (err) {
      const detail = err?.response?.data?.detail || `Failed to load ${title.toLowerCase()}`;
      setError(detail);
      pushToast({ title: 'Load failed', description: String(detail), variant: 'error' });
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
        if (field.type === 'number') {
          acc[field.name] = Number(acc[field.name]);
        }
        if (field.nullable && acc[field.name] === '') {
          acc[field.name] = null;
        }
        return acc;
      }, payload);

      if (createTransform) {
        payload = createTransform(payload);
      }

      await apiClient.post(endpoint, payload);
      setCreateValues(initialCreateState);
      pushToast({ title: 'Saved', description: `${title.slice(0, -1)} created successfully.`, variant: 'success' });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || `Failed to create ${title.toLowerCase()}`;
      setError(typeof detail === 'string' ? detail : 'Request failed');
      pushToast({ title: 'Create failed', description: String(detail), variant: 'error' });
    }
  }

  async function onDelete(row) {
    try {
      await apiClient.delete(`${normalizedEndpoint}/${row.id}`);
      pushToast({ title: 'Deleted', description: `${title.slice(0, -1)} removed.`, variant: 'success' });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail || `Failed to delete ${title.toLowerCase()}`;
      pushToast({ title: 'Delete failed', description: String(detail), variant: 'error' });
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
                <FormInput
                  key={field.name}
                  label={field.label}
                  type={field.type || 'text'}
                  value={filterValues[field.name]}
                  placeholder={field.placeholder}
                  onChange={(e) => onFilterChange(field.name, e.target.value)}
                />
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
                <FormInput
                  key={field.name}
                  label={field.label}
                  type={field.type || 'text'}
                  min={field.min}
                  max={field.max}
                  required={field.required}
                  value={createValues[field.name]}
                  placeholder={field.placeholder}
                  onChange={(e) => onCreateChange(field.name, e.target.value)}
                />
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
          <Table columns={columns} data={rows} onDelete={enableDelete ? onDelete : undefined} />
        </Card>
      </motion.div>
    </div>
  );
}
