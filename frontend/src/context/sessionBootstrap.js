const EMPTY_BRANDING = Object.freeze({
  has_logo: false,
  updated_at: null,
  filename: null
});

const SESSION_BOOTSTRAP_TRANSPORT_KEY = 'caps_ai_session_bootstrap_transport';

let sessionBootstrapTransport = readStoredTransport();

function readStoredTransport() {
  try {
    const value = globalThis.sessionStorage?.getItem(SESSION_BOOTSTRAP_TRANSPORT_KEY) || 'unknown';
    return value === 'legacy' || value === 'consolidated' ? value : 'unknown';
  } catch {
    return 'unknown';
  }
}

function writeStoredTransport(value) {
  sessionBootstrapTransport = value;
  try {
    globalThis.sessionStorage?.setItem(SESSION_BOOTSTRAP_TRANSPORT_KEY, value);
  } catch {
    // Ignore sessionStorage persistence failures for transport mode.
  }
}

function isMissingSessionBootstrapRoute(error) {
  const statusCode = error?.response?.status;
  return statusCode === 404 || statusCode === 405;
}

function normalizeBranding(payload) {
  if (!payload || typeof payload !== 'object') {
    return { ...EMPTY_BRANDING };
  }
  return {
    has_logo: Boolean(payload.has_logo),
    updated_at: payload.updated_at ?? null,
    filename: payload.filename ?? null
  };
}

function normalizeSessionBootstrapPayload(payload) {
  if (!payload?.user) {
    throw new Error('Session bootstrap payload is missing user');
  }
  return {
    user: payload.user,
    unread_notice_count: Number(payload.unread_notice_count) || 0,
    branding: normalizeBranding(payload.branding),
    generated_at: payload.generated_at || new Date().toISOString()
  };
}

async function fetchLegacySessionBootstrap(apiClient) {
  const [userResult, unreadResult, brandingResult] = await Promise.allSettled([
    apiClient.get('/auth/me'),
    apiClient.get('/notices/unread-count'),
    apiClient.get('/branding/logo/meta')
  ]);

  if (userResult.status !== 'fulfilled') {
    throw userResult.reason;
  }

  return normalizeSessionBootstrapPayload({
    user: userResult.value?.data || null,
    unread_notice_count:
      unreadResult.status === 'fulfilled' ? Number(unreadResult.value?.data?.count) || 0 : 0,
    branding: brandingResult.status === 'fulfilled' ? brandingResult.value?.data : EMPTY_BRANDING,
    generated_at: new Date().toISOString()
  });
}

export async function fetchSessionBootstrap(apiClient) {
  if (sessionBootstrapTransport !== 'legacy') {
    try {
      const response = await apiClient.get('/session/bootstrap');
      writeStoredTransport('consolidated');
      return normalizeSessionBootstrapPayload(response?.data);
    } catch (error) {
      if (!isMissingSessionBootstrapRoute(error)) {
        throw error;
      }
      writeStoredTransport('legacy');
    }
  }

  return await fetchLegacySessionBootstrap(apiClient);
}

export function resetSessionBootstrapTransportCache() {
  try {
    globalThis.sessionStorage?.removeItem(SESSION_BOOTSTRAP_TRANSPORT_KEY);
  } catch {
    // Ignore sessionStorage cleanup failures in tests and private contexts.
  }
  sessionBootstrapTransport = 'unknown';
}
