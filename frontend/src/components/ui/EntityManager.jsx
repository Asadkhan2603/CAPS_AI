import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, RefreshCw, Search as SearchIcon } from 'lucide-react';
import Card from './Card';
import EmptyState from './EmptyState';
import InlineErrorState from './InlineErrorState';
import PageLoader from './PageLoader';
import Table from './Table';
import DeleteReviewPrompt from './entityManager/DeleteReviewPrompt';
import EntityFormOverlay from './entityManager/EntityFormOverlay';
import EntitySearchOverlay from './entityManager/EntitySearchOverlay';
import { useDeleteGovernance } from './entityManager/useDeleteGovernance';
import { FEATURE_ACCESS } from '../../config/featureAccess';
import { apiClient } from '../../services/apiClient';
import { invalidateLookupCacheForPath } from '../../services/paginatedLookups';
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
const EMPTY_DELETE_GOVERNANCE = Object.freeze({});

function getFeatureKeyFromPath(...paths) {
  const rawPath = paths.find(Boolean);
  if (!rawPath) return null;

  const segments = String(rawPath).split('?')[0].split('/').filter(Boolean);
  const key = segments.at(-1) || null;
  if (key === 'classes') return 'sections';
  return key;
}

function buildInitialValues(fields = []) {
  return fields.reduce((acc, item) => {
    acc[item.name] = item.defaultValue ?? (item.type === 'number' ? (item.nullable ? '' : 0) : '');
    return acc;
  }, {});
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
  const configuredDeleteGovernance = FEATURE_ACCESS[resolvedFeatureKey]?.deleteGovernance ?? EMPTY_DELETE_GOVERNANCE;
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
  const [editingRowId, setEditingRowId] = useState(null);
  const [searchOverlayOpen, setSearchOverlayOpen] = useState(false);
  const [formOverlayOpen, setFormOverlayOpen] = useState(false);

  const singularTitle = useMemo(() => {
    if (!title) return 'Item';
    if (title.endsWith('ies')) return `${title.slice(0, -3)}y`;
    if (title.endsWith('s')) return title.slice(0, -1);
    return title;
  }, [title]);
  const {
    closeDeleteReviewPrompt,
    deleteError,
    deleteReviewId,
    deleteReviewMetadata,
    deleteReviewPromptConfig,
    deleteReviewPromptOpen,
    deleteReviewTarget,
    onDelete,
    setDeleteReviewId,
    setDeleteReviewMetadata
  } = useDeleteGovernance({
    deletePath,
    deleteReviewConfig,
    loadData,
    pushToast,
    singularTitle,
    title
  });

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

  function resolveSelectedLabel(field, mode, nextCreateValues = createValues, nextFilterValues = searchDraftValues) {
    if (typeof field.selectedLabelResolver === 'function') {
      return (
        field.selectedLabelResolver({
          mode,
          createValues: nextCreateValues,
          filterValues: nextFilterValues,
          rows
        }) || ''
      );
    }

    const currentValue = mode === 'create' ? nextCreateValues?.[field.name] : nextFilterValues?.[field.name];
    if (currentValue === '' || currentValue === null || currentValue === undefined) {
      return '';
    }
    const options = resolveFieldOptions(field, mode, nextCreateValues, nextFilterValues);
    const selected = options.find((option) => String(option.value) === String(currentValue));
    return selected?.label || '';
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
        invalidateLookupCacheForPath(updatePath);
      } else {
        await apiClient.post(createPath, payload);
        invalidateLookupCacheForPath(createPath);
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
          {loading ? <PageLoader compact label={`Loading ${title.toLowerCase()}...`} /> : null}
          {error ? (
            <InlineErrorState
              compact
              title="Load failed"
              description={error}
              onRetry={() => loadData()}
            />
          ) : null}
          {deleteError && !deleteReviewPromptOpen ? <p className="text-sm text-rose-600">{deleteError}</p> : null}
          {!loading && !error ? (
            rows.length ? (
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
            ) : (
              <EmptyState
                title={`No ${title.toLowerCase()} found`}
                description={`There are no ${title.toLowerCase()} matching the current filters.`}
                action={filters.length ? (
                  <button type="button" className="btn-secondary" onClick={() => void resetFilters()}>
                    Reset Filters
                  </button>
                ) : null}
              />
            )
          ) : null}
        </Card>
      </motion.div>

      <EntitySearchOverlay
        applyFilters={applyFilters}
        closeSearchOverlay={closeSearchOverlay}
        createValues={createValues}
        fields={filters}
        filterValues={searchDraftValues}
        onSearchDraftChange={onSearchDraftChange}
        open={searchOverlayOpen}
        resetFilters={resetFilters}
        resolveFieldOptions={resolveFieldOptions}
        resolveSelectedLabel={resolveSelectedLabel}
        rows={rows}
        title={title}
      />

      <EntityFormOverlay
        activeFormFields={activeFormFields}
        closeFormOverlay={closeFormOverlay}
        createValues={createValues}
        editingRowId={editingRowId}
        filterValues={searchDraftValues}
        onCreateChange={onCreateChange}
        onSubmit={onSubmit}
        open={formOverlayOpen}
        resolveFieldOptions={resolveFieldOptions}
        resolveSelectedLabel={resolveSelectedLabel}
        rows={rows}
        singularTitle={singularTitle}
      />

      <DeleteReviewPrompt
        deleteError={deleteError}
        deleteReviewId={deleteReviewId}
        deleteReviewMetadata={deleteReviewMetadata}
        deleteReviewPromptConfig={deleteReviewPromptConfig}
        deleteReviewPromptOpen={deleteReviewPromptOpen}
        deleteReviewTarget={deleteReviewTarget}
        onClose={closeDeleteReviewPrompt}
        onRetry={onDelete}
        setDeleteReviewId={setDeleteReviewId}
        setDeleteReviewMetadata={setDeleteReviewMetadata}
      />
    </div>
  );
}
