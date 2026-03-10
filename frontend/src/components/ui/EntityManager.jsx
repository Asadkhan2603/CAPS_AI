import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, RefreshCw, Search as SearchIcon } from 'lucide-react';
import Card from './Card';
import FormInput from './FormInput';
import Modal from './Modal';
import SearchableSelect from './SearchableSelect';
import Table from './Table';
import { FEATURE_ACCESS } from '../../config/featureAccess';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';

const DEFAULT_DELETE_REVIEW_CONFIG = {
  enabled: false,
  label: 'Approved Review ID',
  placeholder: 'Enter review_id when governance approval is required',
  helpText:
    'Governance-gated deletes require an approved review_id. If the two-person rule is enabled, delete requests without this value will be rejected.',
  promptTitle: 'Governance Review Required',
  promptDescription:
    'This delete operation requires an approved governance review. Enter the approved review_id and any supporting metadata before retrying the delete.',
  metadataFields: []
};

function getFeatureKeyFromPath(...paths) {
  const rawPath = paths.find(Boolean);
  if (!rawPath) return null;

  const segments = String(rawPath).split('?')[0].split('/').filter(Boolean);
  const key = segments.at(-1) || null;
  if (key === 'classes') return 'sections';
  return key;
}

function buildInitialReviewMetadata(fields = []) {
  return fields.reduce((acc, field) => {
    acc[field.name] = field.defaultValue ?? '';
    return acc;
  }, {});
}

function buildInitialValues(fields = []) {
  return fields.reduce((acc, item) => {
    acc[item.name] = item.defaultValue ?? (item.type === 'number' ? (item.nullable ? '' : 0) : '');
    return acc;
  }, {});
}

function extractReviewRequirement(err, fallbackMessage) {
  const data = err?.response?.data ?? {};
  const detail = data?.detail;
  const errorDetail = data?.error?.detail;
  const explicitFlag =
    data?.delete_requires_review ??
    data?.error?.delete_requires_review ??
    detail?.delete_requires_review ??
    errorDetail?.delete_requires_review;

  let required = false;
  let overrides = {};

  if (typeof explicitFlag === 'boolean') {
    required = explicitFlag;
  } else if (explicitFlag && typeof explicitFlag === 'object') {
    required = explicitFlag.required ?? true;
    overrides = explicitFlag;
  }

  const textualHints = [
    fallbackMessage,
    data?.message,
    data?.error?.message,
    typeof detail === 'string' ? detail : null,
    typeof errorDetail === 'string' ? errorDetail : null
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (!required) {
    required =
      textualHints.includes('review_id') ||
      textualHints.includes('approval required') ||
      textualHints.includes('governance approval');
  }

  if (!required) {
    return { required: false, overrides: {} };
  }

  const detailObject = typeof detail === 'object' && detail !== null ? detail : {};
  const errorDetailObject = typeof errorDetail === 'object' && errorDetail !== null ? errorDetail : {};

  return {
    required: true,
    overrides: {
      label:
        overrides.label ??
        data?.review_id_label ??
        detailObject.review_id_label ??
        errorDetailObject.review_id_label,
      placeholder:
        overrides.placeholder ??
        data?.review_id_placeholder ??
        detailObject.review_id_placeholder ??
        errorDetailObject.review_id_placeholder,
      helpText:
        overrides.helpText ??
        data?.review_help_text ??
        detailObject.review_help_text ??
        errorDetailObject.review_help_text,
      promptTitle:
        overrides.promptTitle ??
        data?.review_prompt_title ??
        detailObject.review_prompt_title ??
        errorDetailObject.review_prompt_title,
      promptDescription:
        overrides.promptDescription ??
        data?.review_prompt_description ??
        detailObject.review_prompt_description ??
        errorDetailObject.review_prompt_description,
      metadataFields:
        overrides.metadataFields ??
        data?.review_metadata_fields ??
        detailObject.review_metadata_fields ??
        errorDetailObject.review_metadata_fields
    }
  };
}

export default function EntityManager({
  title,
  endpoint,
  listEndpoint,
  createEndpoint,
  updateEndpoint,
  deleteEndpoint,
  featureKey,
  filters = [],
  createFields = [],
  editFields,
  columns = [],
  pageSizeOptions = [5, 10, 20],
  createTransform,
  updateTransform,
  enableDelete = false,
  enableEdit = false,
  hideCreate = false,
  deleteReviewEnabled = false,
  deleteReviewLabel,
  deleteReviewPlaceholder,
  deleteReviewHelpText,
  deleteReviewPromptTitle,
  deleteReviewPromptDescription,
  deleteReviewMetadataFields,
  rowActions = []
}) {
  const ensureTrailingSlash = (path) => `${String(path || '').replace(/\/+$/, '')}/`;
  const listPath = ensureTrailingSlash(listEndpoint || endpoint);
  const createPath = ensureTrailingSlash(createEndpoint || endpoint);
  const updatePath = ensureTrailingSlash(updateEndpoint || endpoint);
  const deletePath = (deleteEndpoint || listEndpoint || endpoint).replace(/\/+$/, '');
  const resolvedFeatureKey = featureKey || getFeatureKeyFromPath(deleteEndpoint, listEndpoint, endpoint);
  const configuredDeleteGovernance = FEATURE_ACCESS[resolvedFeatureKey]?.deleteGovernance || {};
  const deleteReviewConfig = useMemo(() => {
    const merged = {
      ...DEFAULT_DELETE_REVIEW_CONFIG,
      ...configuredDeleteGovernance,
      ...(deleteReviewEnabled ? { enabled: true } : {}),
      ...(deleteReviewLabel ? { label: deleteReviewLabel } : {}),
      ...(deleteReviewPlaceholder ? { placeholder: deleteReviewPlaceholder } : {}),
      ...(deleteReviewHelpText ? { helpText: deleteReviewHelpText } : {}),
      ...(deleteReviewPromptTitle ? { promptTitle: deleteReviewPromptTitle } : {}),
      ...(deleteReviewPromptDescription ? { promptDescription: deleteReviewPromptDescription } : {}),
      ...(deleteReviewMetadataFields ? { metadataFields: deleteReviewMetadataFields } : {})
    };

    merged.metadataFields = Array.isArray(merged.metadataFields) ? merged.metadataFields : [];
    merged.enabled = Boolean(merged.enabled);
    return merged;
  }, [
    configuredDeleteGovernance,
    deleteReviewEnabled,
    deleteReviewHelpText,
    deleteReviewLabel,
    deleteReviewMetadataFields,
    deleteReviewPlaceholder,
    deleteReviewPromptDescription,
    deleteReviewPromptTitle
  ]);
  const { pushToast } = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(pageSizeOptions[1] ?? 10);
  const [error, setError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deleteReviewId, setDeleteReviewId] = useState('');
  const [deleteReviewMetadata, setDeleteReviewMetadata] = useState(() => buildInitialReviewMetadata(deleteReviewConfig.metadataFields));
  const [deleteReviewPromptOpen, setDeleteReviewPromptOpen] = useState(false);
  const [deleteReviewTarget, setDeleteReviewTarget] = useState(null);
  const [deleteReviewPromptConfig, setDeleteReviewPromptConfig] = useState(deleteReviewConfig);
  const [editingRowId, setEditingRowId] = useState(null);
  const [searchOverlayOpen, setSearchOverlayOpen] = useState(false);
  const [formOverlayOpen, setFormOverlayOpen] = useState(false);

  const singularTitle = useMemo(() => {
    if (!title) return 'Item';
    if (title.endsWith('ies')) return `${title.slice(0, -3)}y`;
    if (title.endsWith('s')) return title.slice(0, -1);
    return title;
  }, [title]);

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
  const initialCreateState = useMemo(() => buildInitialValues(createFields), [createFields]);
  const editFormFields = editFields || createFields;
  const activeFormFields = editingRowId ? editFormFields : createFields;

  const [filterValues, setFilterValues] = useState(initialFilterState);
  const [searchDraftValues, setSearchDraftValues] = useState(initialFilterState);
  const [createValues, setCreateValues] = useState(initialCreateState);

  useEffect(() => {
    setFilterValues(initialFilterState);
    setSearchDraftValues(initialFilterState);
  }, [initialFilterState]);

  useEffect(() => {
    if (!editingRowId) {
      setCreateValues(initialCreateState);
    }
  }, [editingRowId, initialCreateState]);

  useEffect(() => {
    setDeleteReviewPromptConfig(deleteReviewConfig);
    setDeleteReviewMetadata((prev) => {
      const next = buildInitialReviewMetadata(deleteReviewConfig.metadataFields);
      for (const key of Object.keys(next)) {
        if (prev[key] !== undefined) {
          next[key] = prev[key];
        }
      }
      return next;
    });
  }, [deleteReviewConfig]);

  async function loadData(options = {}) {
    const nextSkip = options.skip ?? skip;
    const nextLimit = options.limit ?? limit;
    const nextFilterValues = options.filterValues ?? filterValues;

    setLoading(true);
    setError('');
    try {
      const params = Object.entries(nextFilterValues).reduce((acc, [key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          acc[key] = value;
        }
        return acc;
      }, {});
      params.skip = nextSkip;
      params.limit = nextLimit;

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

  function resolveFieldOptions(field, mode, nextCreateValues = createValues, nextFilterValues = searchDraftValues) {
    const rawOptions =
      typeof field.optionsResolver === 'function'
        ? field.optionsResolver({
            mode,
            createValues: nextCreateValues,
            filterValues: nextFilterValues,
            rows
          })
        : field.options || [];

    const options = Array.isArray(rawOptions) ? rawOptions : [];
    const dependsOn = mode === 'create' ? field.dependsOn : field.filterDependsOn ?? field.dependsOn;
    const matchKey =
      mode === 'create'
        ? field.optionMatchKey || dependsOn
        : field.filterOptionMatchKey || field.optionMatchKey || dependsOn;
    const requireParentSelection =
      mode === 'create'
        ? Boolean(field.requireParentSelection)
        : Boolean(field.filterRequireParentSelection ?? field.requireParentSelection);

    if (!dependsOn) {
      return options;
    }

    const parentValue = mode === 'create' ? nextCreateValues?.[dependsOn] : nextFilterValues?.[dependsOn];

    if ((parentValue === '' || parentValue === null || parentValue === undefined) && requireParentSelection) {
      return [];
    }

    if (parentValue === '' || parentValue === null || parentValue === undefined) {
      return options;
    }

    return options.filter((option) => String(option?.[matchKey]) === String(parentValue));
  }

  function onSearchDraftChange(name, value) {
    setSearchDraftValues((prev) => {
      const next = { ...prev, [name]: value };

      for (const field of filters) {
        const dependsOn = field.filterDependsOn ?? field.dependsOn;
        if (dependsOn !== name) continue;
        const currentValue = next[field.name];
        if (currentValue === '' || currentValue === null || currentValue === undefined) continue;

        const options = resolveFieldOptions(field, 'filter', createValues, next);
        const stillValid = options.some((option) => String(option.value) === String(currentValue));
        if (!stillValid) {
          next[field.name] = '';
        }
      }

      return next;
    });
  }

  function onCreateChange(name, value) {
    setCreateValues((prev) => {
      const next = { ...prev, [name]: value };

      for (const field of activeFormFields) {
        if (field.dependsOn !== name) continue;
        const currentValue = next[field.name];
        if (currentValue === '' || currentValue === null || currentValue === undefined) continue;

        const options = resolveFieldOptions(field, 'create', next, searchDraftValues);
        const stillValid = options.some((option) => String(option.value) === String(currentValue));
        if (!stillValid) {
          next[field.name] = '';
        }
      }

      return next;
    });
  }

  function openSearchOverlay() {
    setSearchDraftValues(filterValues);
    setSearchOverlayOpen(true);
  }

  function closeSearchOverlay() {
    setSearchDraftValues(filterValues);
    setSearchOverlayOpen(false);
  }

  async function applyFilters() {
    const nextFilterValues = { ...searchDraftValues };
    setFilterValues(nextFilterValues);
    setSkip(0);
    setSearchOverlayOpen(false);
    await loadData({ skip: 0, limit, filterValues: nextFilterValues });
  }

  async function resetFilters() {
    setFilterValues(initialFilterState);
    setSearchDraftValues(initialFilterState);
    setSkip(0);
    await loadData({ skip: 0, limit, filterValues: initialFilterState });
  }

  function openCreateOverlay() {
    setEditingRowId(null);
    setCreateValues(initialCreateState);
    setFormOverlayOpen(true);
  }

  function closeFormOverlay() {
    setFormOverlayOpen(false);
    setEditingRowId(null);
    setCreateValues(initialCreateState);
  }

  function startEdit(row) {
    const nextValues = editFormFields.reduce((acc, field) => {
      if (row[field.name] !== undefined && row[field.name] !== null) {
        acc[field.name] = row[field.name];
      } else {
        acc[field.name] = field.defaultValue ?? (field.type === 'number' ? 0 : '');
      }
      return acc;
    }, {});
    setCreateValues(nextValues);
    setEditingRowId(row.id);
    setFormOverlayOpen(true);
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    try {
      let payload = { ...createValues };
      payload = activeFormFields.reduce((acc, field) => {
        if (field.nullable && acc[field.name] === '') {
          acc[field.name] = null;
        }
        if (field.type === 'number') {
          const currentValue = acc[field.name];
          if (currentValue === null || currentValue === undefined || currentValue === '') {
            acc[field.name] = field.nullable ? null : 0;
          } else {
            acc[field.name] = Number(currentValue);
          }
        }
        if (field.type === 'datetime' && acc[field.name]) {
          acc[field.name] = new Date(acc[field.name]).toISOString();
        }
        return acc;
      }, payload);

      if (editingRowId && updateTransform) {
        payload = updateTransform(payload);
      } else if (!editingRowId && createTransform) {
        payload = createTransform(payload);
      }

      if (editingRowId) {
        await apiClient.put(`${updatePath}${editingRowId}`, payload);
      } else {
        await apiClient.post(createPath, payload);
      }

      pushToast({
        title: 'Saved',
        description: editingRowId ? `${singularTitle} updated successfully.` : `${singularTitle} created successfully.`,
        variant: 'success'
      });
      closeFormOverlay();
      await loadData();
    } catch (err) {
      const action = editingRowId ? 'update' : 'create';
      const message = formatApiError(err, `Failed to ${action} ${title.toLowerCase()}`);
      setError(message);
      pushToast({ title: editingRowId ? 'Update failed' : 'Create failed', description: message, variant: 'error' });
    }
  }

  function closeDeleteReviewPrompt() {
    setDeleteReviewPromptOpen(false);
    setDeleteReviewTarget(null);
    setDeleteReviewPromptConfig(deleteReviewConfig);
  }

  function buildDeleteConfig(reviewId = deleteReviewId, metadata = deleteReviewMetadata) {
    const trimmedReviewId = String(reviewId || '').trim();
    const normalizedMetadata = Object.entries(metadata || {}).reduce((acc, [key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        acc[key] = value;
      }
      return acc;
    }, {});

    const params = {};
    if (trimmedReviewId) {
      params.review_id = trimmedReviewId;
    }
    if (Object.keys(normalizedMetadata).length > 0) {
      params.review_metadata = JSON.stringify(normalizedMetadata);
    }

    return Object.keys(params).length ? { params } : undefined;
  }

  async function onDelete(row, options = {}) {
    const { reviewId = deleteReviewId, metadata = deleteReviewMetadata } = options;
    const trimmedReviewId = String(reviewId || '').trim();
    const deleteConfig = buildDeleteConfig(reviewId, metadata);
    try {
      setDeleteError('');
      await apiClient.delete(`${deletePath}/${row.id}`, deleteConfig);
      setDeleteError('');
      pushToast({ title: 'Deleted', description: `${title.slice(0, -1)} removed.`, variant: 'success' });
      closeDeleteReviewPrompt();
      await loadData();
    } catch (err) {
      const message = formatApiError(err, `Failed to delete ${title.toLowerCase()}`);
      const governanceState = extractReviewRequirement(err, message);

      if (governanceState.required) {
        console.warn(`[EntityManager:${title}] delete blocked by governance approval`, {
          rowId: row.id,
          reviewId: trimmedReviewId || null,
          reviewMetadata: metadata,
          message
        });
        setDeleteReviewTarget(row);
        setDeleteReviewPromptConfig((prev) => ({
          ...prev,
          ...governanceState.overrides,
          metadataFields: Array.isArray(governanceState.overrides.metadataFields)
            ? governanceState.overrides.metadataFields
            : prev.metadataFields
        }));
        setDeleteReviewPromptOpen(true);
        pushToast({ title: 'Governance approval required', description: message, variant: 'warning' });
      } else {
        console.error(`[EntityManager:${title}] delete failed`, {
          rowId: row.id,
          reviewId: trimmedReviewId || null,
          reviewMetadata: metadata,
          message
        });
        pushToast({ title: 'Delete failed', description: message, variant: 'error' });
      }

      setDeleteError(message);
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold">{title}</h1>
            <div className="flex items-center gap-2">
              {filters.length ? (
                <button
                  type="button"
                  className="btn-secondary !p-2"
                  onClick={openSearchOverlay}
                  title={`Search ${title}`}
                  aria-label={`Search ${title}`}
                >
                  <SearchIcon size={18} />
                </button>
              ) : null}
              {!hideCreate ? (
                <button
                  type="button"
                  className="btn-secondary !p-2"
                  onClick={openCreateOverlay}
                  title={`Create ${singularTitle}`}
                  aria-label={`Create ${singularTitle}`}
                >
                  <Plus size={18} />
                </button>
              ) : null}
              <button type="button" className="btn-secondary" onClick={() => loadData()}>
                <span className="inline-flex items-center gap-2">
                  <RefreshCw size={16} />
                  Refresh
                </span>
              </button>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{title} List</h2>
            <div className="flex items-center gap-2">
              <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>
                Prev
              </button>
              <span className="text-xs text-slate-500">skip: {skip}</span>
              <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>
                Next
              </button>
              <select className="input w-24" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {enableDelete && deleteReviewConfig.enabled ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-end">
                <p>{deleteReviewConfig.helpText}</p>
                <FormInput
                  label={deleteReviewConfig.label}
                  value={deleteReviewId}
                  placeholder={deleteReviewConfig.placeholder}
                  onChange={(e) => setDeleteReviewId(e.target.value)}
                />
              </div>
            </div>
          ) : null}

          {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          {deleteError ? <p className="text-sm text-rose-600">{deleteError}</p> : null}
          <Table
            columns={columns}
            data={rows}
            onEdit={enableEdit ? startEdit : undefined}
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

      <Modal open={searchOverlayOpen} title={`Search ${title}`} onClose={closeSearchOverlay} size="large">
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {filters.map((field) =>
              field.type === 'switch' ? (
                <label key={field.name} className="block space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{field.label}</span>
                  <button
                    type="button"
                    className="inline-flex h-11 min-w-[8.5rem] items-center justify-center rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                    onClick={() => {
                      const current = searchDraftValues[field.name];
                      const next = current === null ? true : current === true ? false : null;
                      onSearchDraftChange(field.name, next);
                    }}
                  >
                    {searchDraftValues[field.name] === null ? 'Any' : searchDraftValues[field.name] ? 'On' : 'Off'}
                  </button>
                </label>
              ) : field.type === 'select' && field.searchable ? (
                <SearchableSelect
                  key={field.name}
                  label={field.label}
                  value={searchDraftValues[field.name]}
                  options={resolveFieldOptions(field, 'filter', createValues, searchDraftValues)}
                  placeholder={field.placeholder || `Search ${field.label}`}
                  allowEmpty
                  emptyLabel={field.placeholder || `All ${field.label}`}
                  onValueChange={(nextValue) => onSearchDraftChange(field.name, nextValue)}
                />
              ) : field.type === 'select' ? (
                <FormInput
                  key={field.name}
                  as="select"
                  label={field.label}
                  value={searchDraftValues[field.name]}
                  onChange={(e) => onSearchDraftChange(field.name, e.target.value)}
                >
                  <option value="">{field.placeholder || `All ${field.label}`}</option>
                  {resolveFieldOptions(field, 'filter', createValues, searchDraftValues).map((option) => (
                    <option key={`${field.name}-${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </FormInput>
              ) : (
                <FormInput
                  key={field.name}
                  label={field.label}
                  type={field.type === 'datetime' ? 'datetime-local' : field.type || 'text'}
                  value={searchDraftValues[field.name]}
                  placeholder={field.placeholder}
                  onChange={(e) => onSearchDraftChange(field.name, e.target.value)}
                />
              )
            )}
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={closeSearchOverlay}>
              Close
            </button>
            <button type="button" className="btn-secondary" onClick={resetFilters}>
              Reset
            </button>
            <button type="button" className="btn-primary" onClick={applyFilters}>
              Apply
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={formOverlayOpen}
        title={editingRowId ? `Edit ${singularTitle}` : `Create ${singularTitle}`}
        onClose={closeFormOverlay}
        size="large"
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {activeFormFields.map((field) =>
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
              ) : field.type === 'select' && field.searchable ? (
                <SearchableSelect
                  key={field.name}
                  label={field.label}
                  value={createValues[field.name]}
                  options={resolveFieldOptions(field, 'create', createValues, searchDraftValues)}
                  placeholder={field.placeholder || `Search ${field.label}`}
                  required={field.required}
                  allowEmpty={!field.required}
                  emptyLabel={field.placeholder || `Select ${field.label}`}
                  onValueChange={(nextValue) => onCreateChange(field.name, nextValue)}
                />
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
                  {resolveFieldOptions(field, 'create', createValues, searchDraftValues).map((option) => (
                    <option key={`${field.name}-${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </FormInput>
              ) : (
                <FormInput
                  key={field.name}
                  label={field.label}
                  type={field.type === 'datetime' ? 'datetime-local' : field.type || 'text'}
                  min={field.min}
                  max={field.max}
                  required={field.required}
                  value={createValues[field.name]}
                  placeholder={field.placeholder}
                  onChange={(e) => onCreateChange(field.name, e.target.value)}
                />
              )
            )}
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={closeFormOverlay}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              {editingRowId ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal open={deleteReviewPromptOpen} title={deleteReviewPromptConfig.promptTitle} onClose={closeDeleteReviewPrompt}>
        <div className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-slate-600 dark:text-slate-300">{deleteReviewPromptConfig.promptDescription}</p>
            {deleteReviewTarget ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                Pending delete target: <span className="font-medium">{deleteReviewTarget.name || deleteReviewTarget.code || deleteReviewTarget.id}</span>
              </div>
            ) : null}
            {deleteError ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {deleteError}
              </div>
            ) : null}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <FormInput
              label={deleteReviewPromptConfig.label}
              value={deleteReviewId}
              placeholder={deleteReviewPromptConfig.placeholder}
              onChange={(e) => setDeleteReviewId(e.target.value)}
            />
            {deleteReviewPromptConfig.metadataFields.map((field) => (
              <FormInput
                key={field.name}
                label={field.label}
                type={field.type || 'text'}
                value={deleteReviewMetadata[field.name] ?? ''}
                placeholder={field.placeholder}
                required={field.required}
                onChange={(e) =>
                  setDeleteReviewMetadata((prev) => ({
                    ...prev,
                    [field.name]: e.target.value
                  }))
                }
              />
            ))}
          </div>

          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={closeDeleteReviewPrompt}>
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                if (!deleteReviewTarget) return;
                onDelete(deleteReviewTarget, { reviewId: deleteReviewId, metadata: deleteReviewMetadata });
              }}
            >
              Retry Delete
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
