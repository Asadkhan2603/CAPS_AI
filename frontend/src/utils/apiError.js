export function formatApiError(err, fallback = 'Request failed') {
  const detail = err?.response?.data?.detail;
  if (!detail) {
    return fallback;
  }
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first?.msg) {
      return String(first.msg);
    }
  }
  if (typeof detail === 'object') {
    if (detail.msg) {
      return String(detail.msg);
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }
  return String(detail);
}
