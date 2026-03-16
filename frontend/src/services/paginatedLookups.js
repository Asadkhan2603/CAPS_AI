import { apiClient } from './apiClient';

const PAGE_SIZE = 100;
const LOOKUP_PAGE_SIZE = 20;
const lookupCache = new Map();

function buildCacheKey(path, params) {
  const entries = Object.entries(params || {}).sort(([left], [right]) => left.localeCompare(right));
  return JSON.stringify([path, entries]);
}

export async function listAllPages(path, params = {}, pageSize = PAGE_SIZE) {
  const rows = [];
  let skip = 0;

  while (true) {
    const response = await apiClient.get(path, {
      params: { ...params, skip, limit: pageSize }
    });
    const items = Array.isArray(response.data) ? response.data : [];
    rows.push(...items);

    if (items.length < pageSize) {
      break;
    }

    skip += pageSize;
  }

  return rows;
}

export async function listAllWithActiveStates(path, params = {}, pageSize = PAGE_SIZE) {
  const [activeRows, inactiveRows] = await Promise.all([
    listAllPages(path, { ...params, is_active: true }, pageSize),
    listAllPages(path, { ...params, is_active: false }, pageSize)
  ]);

  const merged = new Map();
  [...activeRows, ...inactiveRows].forEach((item) => {
    if (item?.id) {
      merged.set(item.id, item);
    }
  });
  return Array.from(merged.values());
}

export async function fetchLookupPage(path, params = {}, pageSize = LOOKUP_PAGE_SIZE) {
  const response = await apiClient.get(path, {
    params: { ...params, skip: params.skip ?? 0, limit: params.limit ?? pageSize }
  });
  return Array.isArray(response.data) ? response.data : [];
}

export async function searchLookupOptions({
  path,
  q = '',
  params = {},
  pageSize = LOOKUP_PAGE_SIZE,
  mapOption = (item) => ({ value: item.id, label: item.name || item.code || item.id })
}) {
  const requestParams = {
    ...params,
    skip: 0,
    limit: pageSize
  };
  if (q?.trim()) {
    requestParams.q = q.trim();
  }

  const cacheKey = buildCacheKey(path, requestParams);
  if (lookupCache.has(cacheKey)) {
    return lookupCache.get(cacheKey);
  }

  const items = await fetchLookupPage(path, requestParams, pageSize);
  const mapped = items.map((item) => mapOption(item, q));
  lookupCache.set(cacheKey, mapped);
  return mapped;
}

export function clearLookupCache(prefix = '') {
  if (!prefix) {
    lookupCache.clear();
    return;
  }
  for (const key of lookupCache.keys()) {
    if (key.includes(prefix)) {
      lookupCache.delete(key);
    }
  }
}

export function mergeLookupItems(currentItems, nextItems, idKey = 'id') {
  const merged = new Map((currentItems || []).map((item) => [item?.[idKey], item]));
  (nextItems || []).forEach((item) => {
    if (item?.[idKey] !== undefined && item?.[idKey] !== null) {
      merged.set(item[idKey], item);
    }
  });
  return Array.from(merged.values());
}
