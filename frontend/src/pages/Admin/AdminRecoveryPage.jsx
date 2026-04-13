import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import Skeleton from '../../components/ui/Skeleton';
import Table from '../../components/ui/Table';
import { useToast } from '../../hooks/useToast';
import {
  getDefaultRecoveryCollection,
  getRecoveryCollectionMeta,
  getRecoveryStatusVariant,
  groupRecoveryCatalog,
} from './adminRecoveryCatalog';
import { buildRecoveryAuditLogPath } from './adminWorkflowLinks';
import { fetchRecoveryItems, restoreRecoveryItem } from '../../services/adminRecoveryApi';
import { formatApiError } from '../../utils/apiError';

const DEFAULT_COLLECTION = 'notices';

export default function AdminRecoveryPage() {
  const { pushToast } = useToast();
  const [collection, setCollection] = useState(DEFAULT_COLLECTION);
  const [catalog, setCatalog] = useState([]);
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({});
  const [timestamp, setTimestamp] = useState(null);
  const [includeLegacy, setIncludeLegacy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [restoreModalItem, setRestoreModalItem] = useState(null);
  const [restoreError, setRestoreError] = useState('');
  const [restoring, setRestoring] = useState(false);
  const [lastRestored, setLastRestored] = useState(null);

  const collectionMeta = getRecoveryCollectionMeta(collection);
  const groupedCatalog = useMemo(() => groupRecoveryCatalog(catalog), [catalog]);
  const recoverableCount = summary?.[collection] ?? items.length;

  useEffect(() => {
    void loadRecovery();
  }, [collection, includeLegacy]);

  async function loadRecovery() {
    setLoading(true);
    setError('');
    try {
      const result = await fetchRecoveryItems({
        collection,
        includeLegacy,
        limit: 100,
      });
      setCatalog(result.catalog);
      setItems(result.items);
      setSummary(result.summary);
      setTimestamp(result.timestamp);
      if (result.collection && result.collection !== collection) {
        setCollection(result.collection);
      }
    } catch (err) {
      setItems([]);
      setSummary({});
      setCatalog([]);
      setTimestamp(null);
      setError(formatApiError(err, 'Failed to load recovery items'));
    } finally {
      setLoading(false);
    }
  }

  function onToggleLegacy() {
    const nextValue = !includeLegacy;
    setIncludeLegacy(nextValue);
    if (!nextValue && getRecoveryCollectionMeta(collection).legacy) {
      setCollection(getDefaultRecoveryCollection(catalog.filter((item) => item.legacy !== true), DEFAULT_COLLECTION));
    }
  }

  function openRestoreModal(row) {
    setRestoreError('');
    setRestoreModalItem(row);
  }

  function closeRestoreModal() {
    if (restoring) return;
    setRestoreError('');
    setRestoreModalItem(null);
  }

  async function confirmRestore() {
    if (!restoreModalItem) return;

    setRestoring(true);
    setRestoreError('');
    try {
      await restoreRecoveryItem(collection, restoreModalItem.id);
      setLastRestored({
        id: restoreModalItem.id,
        displayName: restoreModalItem.display_name,
        collection,
        collectionLabel: collectionMeta.label,
      });
      pushToast({
        title: 'Restore completed',
        description: `${restoreModalItem.display_name} was restored successfully.`,
        variant: 'success',
      });
      setRestoreModalItem(null);
      await loadRecovery();
    } catch (err) {
      const message = formatApiError(err, 'Restore failed');
      setRestoreError(message);
      pushToast({
        title: 'Restore failed',
        description: message,
        variant: 'error',
      });
    } finally {
      setRestoring(false);
    }
  }

  const tableColumns = [
    {
      key: 'item',
      label: 'Item',
      render: (row) => (
        <div className="space-y-1">
          <div className="font-medium text-slate-900 dark:text-slate-100">{row.display_name}</div>
          <div className="text-xs text-slate-500">{row.subtitle || 'N/A'}</div>
        </div>
      ),
    },
    {
      key: 'status_label',
      label: 'Category / Status',
      render: (row) => (
        <div className="space-y-1">
          <div className="text-sm text-slate-700 dark:text-slate-200">{row.collectionLabel}</div>
          <Badge variant={getRecoveryStatusVariant(row.status_label)}>{row.status_label}</Badge>
        </div>
      ),
    },
    {
      key: 'deleted_at',
      label: 'Deleted At',
      render: (row) => formatDateTime(row.deleted_at),
    },
    {
      key: 'deleted_by_label',
      label: 'Deleted By',
      render: (row) => row.deleted_by_label || 'N/A',
    },
    {
      key: 'advanced',
      label: 'Advanced Details',
      render: (row) => (
        <div className="space-y-1 text-xs text-slate-500">
          <div>Collection: {row.collection}</div>
          <div>Record ID: {row.id}</div>
          <div>Audit type: {row.audit_resource_type}</div>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-2">
            <div>
              <h1 className="text-2xl font-semibold">Recovery</h1>
              <p className="text-sm text-slate-500">
                Review soft-deleted records carefully, confirm context, and restore only when the audit trail matches the intent.
              </p>
            </div>
            <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
              Restore actions are audited. Use this workspace for deliberate recovery, not bulk correction.
            </p>
          </div>
          <Link className="btn-secondary w-fit" to="/audit-logs">
            Open Audit Logs
          </Link>
        </div>
      </Card>

      {lastRestored ? (
        <Card className="space-y-3 border border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-100">Restore completed</p>
              <p className="text-sm text-emerald-800 dark:text-emerald-200">
                {lastRestored.displayName} was restored in {lastRestored.collectionLabel}.
              </p>
            </div>
            <Link
              className="btn-secondary w-fit"
              to={buildRecoveryAuditLogPath(lastRestored.collection)}
            >
              View restore audit trail
            </Link>
          </div>
        </Card>
      ) : null}

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Collection Selector</h2>
            <p className="text-sm text-slate-500">Choose what type of deleted record you want to inspect before restoring.</p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={includeLegacy}
              onChange={onToggleLegacy}
            />
            Include legacy collections
          </label>
        </div>
        <div className="space-y-4">
          {groupedCatalog.map((entry) => (
            <div key={entry.group} className="space-y-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{entry.group}</h3>
                {entry.group === 'Legacy' ? <Badge variant="warning">Legacy</Badge> : null}
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {entry.items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setCollection(item.key)}
                    className={`rounded-2xl border px-4 py-4 text-left transition ${
                      collection === item.key
                        ? 'border-brand-400 bg-brand-50 text-brand-900 dark:border-brand-700 dark:bg-brand-900/20 dark:text-brand-200'
                        : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/60 dark:hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{item.label}</p>
                      {item.legacy ? <Badge variant="warning">Legacy</Badge> : null}
                    </div>
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{item.description}</p>
                    <p className="mt-2 text-xs text-slate-400">Raw key: {item.key}</p>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Recovery Summary</h2>
          <p className="text-sm text-slate-500">Current context for the selected restore category.</p>
        </div>
        {loading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-24" />
            ))}
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryMetric label="Selected Collection" value={collectionMeta.label} detail={`Group: ${collectionMeta.group}`} />
            <SummaryMetric label="Recoverable Rows" value={recoverableCount} detail="Soft-deleted rows currently available to review." />
            <SummaryMetric label="Last Refresh" value={formatDateTime(timestamp)} detail="Latest recovery snapshot timestamp." />
            <SummaryMetric label="Legacy Mode" value={includeLegacy ? 'Included' : 'Active Only'} detail="Legacy categories stay opt-in for safer browsing." />
          </div>
        )}
      </Card>

      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}

      <Card className="space-y-4">
        <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Recoverable Items</h2>
            <p className="text-sm text-slate-500">
              Review the item context before opening the restore confirmation flow.
            </p>
          </div>
          <button className="btn-secondary w-fit" type="button" onClick={() => void loadRecovery()} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-28" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="No recoverable items in this category"
            description={`There are no soft-deleted ${collectionMeta.label.toLowerCase()} waiting for restore review right now.`}
          />
        ) : (
          <>
            <div className="space-y-3 md:hidden">
              {items.map((row) => (
                <Card key={row.id} className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-slate-100">{row.display_name}</p>
                      <p className="text-sm text-slate-500">{row.subtitle || 'N/A'}</p>
                    </div>
                    <Badge variant={getRecoveryStatusVariant(row.status_label)}>{row.status_label}</Badge>
                  </div>
                  <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <div>Category: {row.collectionLabel}</div>
                    <div>Deleted at: {formatDateTime(row.deleted_at)}</div>
                    <div>Deleted by: {row.deleted_by_label || 'N/A'}</div>
                  </div>
                  <div className="rounded-xl border border-dashed border-slate-200 px-3 py-2 text-xs text-slate-500 dark:border-slate-700">
                    <div>Collection key: {row.collection}</div>
                    <div>Record ID: {row.id}</div>
                    <div>Audit type: {row.audit_resource_type}</div>
                  </div>
                  <button className="btn-secondary w-fit" type="button" onClick={() => openRestoreModal(row)}>
                    Review Restore
                  </button>
                </Card>
              ))}
            </div>
            <div className="hidden md:block">
              <Table
                columns={tableColumns}
                data={items}
                rowActions={[{ key: 'restore', label: 'Review Restore', onClick: openRestoreModal }]}
              />
            </div>
          </>
        )}
      </Card>

      <Modal open={Boolean(restoreModalItem)} onClose={closeRestoreModal} title="Confirm Restore">
        {restoreModalItem ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-700 dark:bg-slate-900/60">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-500">Collection</p>
                  <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{collectionMeta.label}</p>
                  <p className="text-xs text-slate-400">Raw key: {collection}</p>
                </div>
                <Badge variant={getRecoveryStatusVariant(restoreModalItem.status_label)}>
                  {restoreModalItem.status_label}
                </Badge>
              </div>
              <div className="mt-4 space-y-2">
                <div>
                  <p className="text-sm font-medium text-slate-500">Item</p>
                  <p className="text-base font-semibold text-slate-900 dark:text-slate-100">{restoreModalItem.display_name}</p>
                  <p className="text-sm text-slate-500">{restoreModalItem.subtitle || 'N/A'}</p>
                </div>
                <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <div>Deleted at: {formatDateTime(restoreModalItem.deleted_at)}</div>
                  <div>Deleted by: {restoreModalItem.deleted_by_label || 'N/A'}</div>
                  <div>Current active state: {restoreModalItem.status_label}</div>
                  <div>Audit resource type: {restoreModalItem.audit_resource_type}</div>
                </div>
              </div>
            </div>

            <p className="text-sm text-slate-500">
              This restore action will be written to the audit trail. Confirm only after verifying the deleted record and business context.
            </p>

            {restoreError ? <p className="text-sm text-rose-600">{restoreError}</p> : null}

            <div className="flex flex-wrap justify-end gap-2">
              <button className="btn-secondary" type="button" onClick={closeRestoreModal} disabled={restoring}>
                Cancel
              </button>
              <button className="btn-primary" type="button" onClick={() => void confirmRestore()} disabled={restoring}>
                {restoring ? 'Restoring...' : 'Confirm Restore'}
              </button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

function SummaryMetric({ label, value, detail }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-700 dark:bg-slate-900/60">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value ?? '-'}</p>
      <p className="mt-2 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

function formatDateTime(value) {
  if (!value) return 'N/A';
  return new Date(value).toLocaleString();
}
