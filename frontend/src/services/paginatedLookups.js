import { apiClient } from './apiClient';

const LOOKUP_PAGE_SIZE = 20;
const LOOKUP_CACHE_TTL_MS = 10 * 60 * 1000;
const LOOKUP_CACHE_NAMESPACE = 'caps_ai_lookup_cache:';
const LOOKUP_CACHE_INDEX_KEY = 'caps_ai_lookup_cache_index';
const lookupCache = new Map();
const lookupInflight = new Map();
const LOOKUP_INVALIDATION_RULES = {
  '/universities/': ['/universities/', '/faculties/', '/departments/', '/programs/', '/specializations/', '/batches/', '/semesters/', '/sections/', '/groups/'],
  '/faculties/': ['/faculties/', '/departments/', '/programs/', '/specializations/', '/batches/', '/semesters/', '/sections/', '/groups/'],
  '/departments/': ['/departments/', '/programs/', '/specializations/', '/batches/', '/semesters/', '/sections/', '/groups/'],
  '/programs/': ['/programs/', '/specializations/', '/batches/', '/semesters/', '/sections/', '/groups/'],
  '/specializations/': ['/specializations/', '/batches/', '/semesters/', '/sections/', '/groups/'],
  '/batches/': ['/batches/', '/semesters/', '/sections/', '/groups/'],
  '/semesters/': ['/semesters/', '/sections/', '/groups/'],
  '/sections/': ['/sections/', '/groups/'],
  '/groups/': ['/groups/'],
  '/subjects/': ['/subjects/', '/course-offerings/'],
  '/clubs/': ['/clubs/'],
  '/course-offerings/': ['/course-offerings/', '/class-slots/'],
  '/class-slots/': ['/class-slots/']
};

function getSessionStore() {
  try {
    return globalThis.sessionStorage || null;
  } catch {
    return null;
  }
}

function buildCacheKey(path, params) {
  const entries = Object.entries(params || {}).sort(([left], [right]) => left.localeCompare(right));
  return JSON.stringify([path, entries]);
}

function buildStorageKey(cacheKey) {
  return `${LOOKUP_CACHE_NAMESPACE}${cacheKey}`;
}

function readCacheIndex(store) {
  if (!store) {
    return [];
  }
  try {
    const raw = store.getItem(LOOKUP_CACHE_INDEX_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeCacheIndex(store, nextIndex) {
  if (!store) {
    return;
  }
  try {
    store.setItem(LOOKUP_CACHE_INDEX_KEY, JSON.stringify(Array.from(new Set(nextIndex))));
  } catch {
    // Ignore storage write failures.
  }
}

function readCachedLookup(cacheKey) {
  const now = Date.now();
  const cached = lookupCache.get(cacheKey);
  if (cached && cached.expiresAt > now) {
    return cached.value;
  }
  if (cached) {
    lookupCache.delete(cacheKey);
  }

  const store = getSessionStore();
  if (!store) {
    return null;
  }

  try {
    const raw = store.getItem(buildStorageKey(cacheKey));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.expiresAt <= now) {
      store.removeItem(buildStorageKey(cacheKey));
      const nextIndex = readCacheIndex(store).filter((item) => item !== cacheKey);
      writeCacheIndex(store, nextIndex);
      return null;
    }
    lookupCache.set(cacheKey, parsed);
    return parsed.value;
  } catch {
    return null;
  }
}

function writeCachedLookup(cacheKey, value, ttlMs = LOOKUP_CACHE_TTL_MS) {
  const entry = {
    value,
    expiresAt: Date.now() + ttlMs
  };
  lookupCache.set(cacheKey, entry);

  const store = getSessionStore();
  if (!store) {
    return;
  }

  try {
    store.setItem(buildStorageKey(cacheKey), JSON.stringify(entry));
    const nextIndex = readCacheIndex(store);
    nextIndex.push(cacheKey);
    writeCacheIndex(store, nextIndex);
  } catch {
    // Ignore storage write failures.
  }
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
  ttlMs = LOOKUP_CACHE_TTL_MS,
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
  const cached = readCachedLookup(cacheKey);
  if (cached) {
    return cached;
  }
  if (lookupInflight.has(cacheKey)) {
    return lookupInflight.get(cacheKey);
  }

  const request = fetchLookupPage(path, requestParams, pageSize)
    .then((items) => {
      const mapped = items.map((item) => mapOption(item, q));
      writeCachedLookup(cacheKey, mapped, ttlMs);
      return mapped;
    })
    .finally(() => {
      lookupInflight.delete(cacheKey);
    });
  lookupInflight.set(cacheKey, request);
  return request;
}

export function clearLookupCache(prefix = '') {
  const normalizedPrefix = String(prefix || '');
  if (!normalizedPrefix) {
    lookupCache.clear();
    lookupInflight.clear();
  } else {
    for (const key of lookupCache.keys()) {
      if (key.includes(normalizedPrefix)) {
        lookupCache.delete(key);
      }
    }
    for (const key of lookupInflight.keys()) {
      if (key.includes(normalizedPrefix)) {
        lookupInflight.delete(key);
      }
    }
  }

  const store = getSessionStore();
  if (!store) {
    return;
  }
  const cacheIndex = readCacheIndex(store);
  const nextIndex = [];
  for (const cacheKey of cacheIndex) {
    const shouldRemove = !normalizedPrefix || cacheKey.includes(normalizedPrefix);
    if (shouldRemove) {
      store.removeItem(buildStorageKey(cacheKey));
    } else {
      nextIndex.push(cacheKey);
    }
  }
  writeCacheIndex(store, nextIndex);
}

export function invalidateLookupCacheForPath(path = '') {
  const normalizedPath = String(path || '').replace(/\/+$/, '/') || '/';
  const prefixes = LOOKUP_INVALIDATION_RULES[normalizedPath];
  if (!prefixes?.length) {
    clearLookupCache(normalizedPath);
    return;
  }
  prefixes.forEach((prefix) => clearLookupCache(prefix));
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
