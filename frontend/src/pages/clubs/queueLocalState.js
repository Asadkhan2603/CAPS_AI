const SAVED_FILTERS_PREFIX = 'clubs.queue.savedFilters';
const SNAPSHOT_HISTORY_PREFIX = 'clubs.queue.snapshotHistory';
const MAX_SAVED_FILTERS = 6;
const MAX_SNAPSHOTS = 12;

function readStorage(key) {
  try {
    const raw = globalThis.localStorage?.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeStorage(key, value) {
  try {
    globalThis.localStorage?.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore localStorage failures in private browsing or tests.
  }
}

function filtersKey(userId, queueType, scopeId) {
  return `${SAVED_FILTERS_PREFIX}.${userId || 'anon'}.${queueType}.${scopeId || 'global'}`;
}

function snapshotsKey(userId, queueType, scopeId) {
  return `${SNAPSHOT_HISTORY_PREFIX}.${userId || 'anon'}.${queueType}.${scopeId || 'global'}`;
}

export function listSavedQueueFilters(userId, queueType, scopeId) {
  return readStorage(filtersKey(userId, queueType, scopeId));
}

export function saveQueueFilter(userId, queueType, scopeId, filter) {
  const key = filtersKey(userId, queueType, scopeId);
  const current = readStorage(key);
  const next = [
    {
      ...filter,
      savedAt: filter.savedAt || new Date().toISOString()
    },
    ...current.filter((item) => item.id !== filter.id)
  ].slice(0, MAX_SAVED_FILTERS);
  writeStorage(key, next);
  return next;
}

export function removeQueueFilter(userId, queueType, scopeId, filterId) {
  const key = filtersKey(userId, queueType, scopeId);
  const next = readStorage(key).filter((item) => item.id !== filterId);
  writeStorage(key, next);
  return next;
}

export function listQueueSnapshots(userId, queueType, scopeId) {
  return readStorage(snapshotsKey(userId, queueType, scopeId));
}

export function recordQueueSnapshot(userId, queueType, scopeId, snapshot) {
  const key = snapshotsKey(userId, queueType, scopeId);
  const current = readStorage(key);
  const signature = snapshot.signature;
  const last = current[0];

  if (last?.signature === signature) {
    return current;
  }

  const next = [
    {
      ...snapshot,
      capturedAt: snapshot.capturedAt || new Date().toISOString()
    },
    ...current
  ].slice(0, MAX_SNAPSHOTS);
  writeStorage(key, next);
  return next;
}
