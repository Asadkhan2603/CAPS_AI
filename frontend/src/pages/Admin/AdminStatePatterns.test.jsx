// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminAnalyticsPage from './AdminAnalyticsPage';
import AdminOnboardingPage from './AdminOnboardingPage';
import AdminObservabilityPage from './AdminObservabilityPage';
import AdminSystemPage from './AdminSystemPage';

const {
  mockApiGet,
  mockPushToast,
  mockUseAdminSystemHealth,
} = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockPushToast: vi.fn(),
  mockUseAdminSystemHealth: vi.fn(),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    get: (...args) => mockApiGet(...args),
  },
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({ pushToast: mockPushToast }),
}));

vi.mock('./system/useAdminSystemHealth', () => ({
  AUTO_REFRESH_MS: 30000,
  useAdminSystemHealth: (...args) => mockUseAdminSystemHealth(...args),
}));

vi.mock('../../components/ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>,
}));

vi.mock('../../components/ui/Badge', () => ({
  default: ({ children }) => <span>{children}</span>,
}));

vi.mock('./system/AlertRoutingHistorySection', () => ({
  default: () => <div>Alert Routing History Mock</div>,
}));

vi.mock('./system/ClubObservabilityTrendSection', () => ({
  default: () => <div>Clubs Pressure Trends Mock</div>,
}));

vi.mock('./system/SystemHealthHistoryCharts', () => ({
  default: () => <div>System Health History Charts Mock</div>,
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function buildHookState(overrides = {}) {
  return {
    aiMetrics: {},
    alertRouteHistory: [],
    alertRouting: {},
    clubsMetrics: {},
    clubsObservability: { summary: {}, hourly24h: [], daily14d: [], recentPressureWindows: [] },
    clearSnapshots: vi.fn(),
    data: {
      timestamp: '2026-04-13T06:00:00.000Z',
      alerts: [],
      observability: { request_metrics: {}, scheduler_metrics: {} },
      collection_counts: {},
      snapshot_history: [],
      slow_query_logs: [],
    },
    error: '',
    exportSnapshots: vi.fn(),
    historyData: [],
    isAutoRefresh: true,
    isRefreshing: false,
    loadHealth: vi.fn(),
    localHistoryData: [],
    localSnapshots: [],
    persistedHistoryData: [],
    setIsAutoRefresh: vi.fn(),
    snapshotStore: {},
    ...overrides,
  };
}

async function renderPage(component, route = '/admin/test') {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(<MemoryRouter initialEntries={[route]}>{component}</MemoryRouter>);
    await waitForTick();
    await waitForTick();
  });
}

describe('Admin state patterns', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockApiGet.mockReset();
    mockPushToast.mockReset();
    mockUseAdminSystemHealth.mockReset();
    mockUseAdminSystemHealth.mockReturnValue(buildHookState());
  });

  afterEach(async () => {
    await act(async () => {
      root?.unmount();
      await waitForTick();
    });
    root = null;
    if (container) {
      container.remove();
    }
    container = null;
    document.body.innerHTML = '';
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = false;
    vi.clearAllMocks();
  });

  it('shows a loading placeholder before analytics data resolves', async () => {
    const pending = deferred();
    mockApiGet.mockReturnValueOnce(pending.promise);

    await renderPage(<AdminAnalyticsPage />, '/admin/analytics');

    expect(document.body.textContent).toContain('Loading analytics snapshot...');
  });

  it('shows retryable error states for analytics and onboarding pages', async () => {
    mockApiGet
      .mockRejectedValueOnce(new Error('analytics down'))
      .mockRejectedValueOnce(new Error('onboarding down'));

    await renderPage(<AdminAnalyticsPage />, '/admin/analytics');

    expect(document.body.textContent).toContain('Analytics unavailable');
    expect(document.body.textContent).toContain('Retry');

    await act(async () => {
      root.unmount();
      await waitForTick();
    });

    await renderPage(<AdminOnboardingPage />, '/admin/onboarding');

    expect(document.body.textContent).toContain('Onboarding overview unavailable');
    expect(document.body.textContent).toContain('Retry');
  });

  it('shows retryable top-level error states for system and observability pages', async () => {
    mockUseAdminSystemHealth
      .mockReturnValueOnce(buildHookState({ data: null, error: 'system failure', isRefreshing: false }))
      .mockReturnValueOnce(buildHookState({ data: null, error: 'diagnostics failure', isRefreshing: false }));

    await renderPage(<AdminSystemPage />, '/admin/system');

    expect(document.body.textContent).toContain('System overview unavailable');
    expect(document.body.textContent).toContain('Retry');

    await act(async () => {
      root.unmount();
      await waitForTick();
    });

    await renderPage(<AdminObservabilityPage />, '/admin/observability');

    expect(document.body.textContent).toContain('Diagnostics unavailable');
    expect(document.body.textContent).toContain('Retry');
  });
});
