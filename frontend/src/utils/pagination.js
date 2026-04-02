export function parsePositiveInt(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function parseNonNegativeInt(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

export function readTotalCount(response, fallback = 0) {
  const rawValue = response?.headers?.['x-total-count'];
  const parsed = Number.parseInt(String(rawValue ?? ''), 10);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

export function getPageFromSkip(skip, limit) {
  return Math.floor(Math.max(0, skip) / Math.max(1, limit)) + 1;
}

export function getPageCount(totalCount, limit) {
  return Math.max(1, Math.ceil(Math.max(0, totalCount) / Math.max(1, limit)));
}
