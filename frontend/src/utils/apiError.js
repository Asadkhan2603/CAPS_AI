export function formatApiError(err, fallback = 'Request failed') {
  const hasResponse = Boolean(err?.response);
  const code = String(err?.code || '');
  const message = String(err?.message || '');
  const detail = err?.response?.data?.detail;
  const errorId = err?.response?.data?.error_id || err?.response?.headers?.['x-error-id'];
  const withId = (message) => (errorId ? `${message} (Error ID: ${errorId})` : message);
  if (!hasResponse) {
    if (code === 'ECONNABORTED' || /timeout/i.test(message)) {
      return 'API request timed out. Check whether the backend is overloaded or unreachable.';
    }
    if (code === 'ERR_NETWORK' || /network error/i.test(message) || /ecconnrefused/i.test(message)) {
      return 'Backend API is not reachable. Start the backend server on port 8000 and try again.';
    }
    return fallback;
  }
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
