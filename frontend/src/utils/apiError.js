export function formatApiError(err, fallback = 'Request failed') {
  const detail = err?.response?.data?.detail;
  const errorId = err?.response?.data?.error_id || err?.response?.headers?.['x-error-id'];
  const withId = (message) => (errorId ? `${message} (Error ID: ${errorId})` : message);
  if (!detail) {
    return withId(fallback);
  }
  if (typeof detail === 'string') {
    return withId(detail);
  }
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first?.msg) {
      return withId(String(first.msg));
    }
  }
  if (typeof detail === 'object') {
    if (detail.msg) {
      return withId(String(detail.msg));
    }
    try {
      return withId(JSON.stringify(detail));
    } catch {
      return withId(fallback);
    }
  }
  return withId(String(detail));
}
