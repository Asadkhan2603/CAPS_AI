import { apiClient } from './apiClient';
import {
  getDefaultRecoveryCollection,
  getRecoveryCollectionMeta,
  normalizeRecoveryCatalog,
} from '../pages/Admin/adminRecoveryCatalog';

export async function fetchRecoveryItems({ collection = '', includeLegacy = false, limit = 100 } = {}) {
  const params = { include_legacy: includeLegacy, limit };
  if (collection) {
    params.collection = collection;
  }

  const response = await apiClient.get('/admin/recovery/', { params });
  const payload = response.data || {};
  const catalog = normalizeRecoveryCatalog(payload.catalog || []);
  const selectedCollection = collection || getDefaultRecoveryCollection(catalog);
  const rawItems = Array.isArray(payload.items?.[selectedCollection]) ? payload.items[selectedCollection] : [];

  return {
    timestamp: payload.timestamp || null,
    catalog,
    summary: payload.summary || {},
    legacyCollectionsIncluded: Boolean(payload.legacy_collections_included),
    collection: selectedCollection,
    items: rawItems.map((item) => normalizeRecoveryItem(selectedCollection, item)),
  };
}

export async function restoreRecoveryItem(collection, itemId) {
  const response = await apiClient.patch(`/admin/recovery/${collection}/${itemId}/restore`);
  return response.data || {};
}

function normalizeRecoveryItem(collection, item = {}) {
  const meta = getRecoveryCollectionMeta(collection);
  return {
    ...item,
    collection,
    collectionLabel: meta.label,
    collectionGroup: meta.group,
    display_name: item.display_name || item.name || item.public_id || item.id || 'N/A',
    subtitle: item.subtitle || 'N/A',
    status_label: item.status_label || 'Unknown',
    deleted_by_label: item.deleted_by_label || item.deleted_by || 'N/A',
    audit_resource_type: item.audit_resource_type || collection,
  };
}
