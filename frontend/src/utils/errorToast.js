import { formatApiError } from './apiError';

const STATUS_TITLE_MAP = {
  400: 'Invalid request',
  401: 'Authentication required',
  403: 'Access denied',
  404: 'Not found',
  409: 'Conflict',
  422: 'Validation failed',
  423: 'Account locked',
  429: 'Too many requests',
  500: 'Server error'
};

export function pushApiErrorToast(pushToast, err, fallback = 'Request failed') {
  const status = err?.response?.status;
  const title = STATUS_TITLE_MAP[status] || 'Request failed';
  pushToast({
    title,
    description: formatApiError(err, fallback),
    variant: 'error'
  });
}
