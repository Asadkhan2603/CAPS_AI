// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminObservabilityPage from './AdminObservabilityPage';
import AdminSystemPage from './AdminSystemPage';
import { getHealthStatusMeta } from './system/adminOperationsViewModel';

const { mockUseAdminSystemHealth, mockPushToast } = vi.hoisted(() => ({
  mockUseAdminSystemHealth: vi.fn(),
  mockPushToast: vi.fn(),
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

function buildHookState(overrides = {}) {
  return {
    aiMetrics: {
      queued_jobs: 4,
      queue_warn_depth: 8,
      queue_critical_depth: 12,
      oldest_queued_age_seconds: 45,
      queue_warn_age_seconds: 90,
      queue_critical_age_seconds: 180,
      fallback_rate_pct_15m: 2.15,
      fallback_warning_rate_pct: 5,
      fallback_critical_rate_pct: 10,
      last_similarity_candidate_count: 7,
      similarity_candidate_warn_threshold: 10,
      similarity_candidate_cap: 20,
    },
    alertRouteHistory: [{ alert_code: 'db.latency' }],
    alertRouting: { enabled: true },
    clubsMetrics: {
      requests_15m: 12,
      p95_duration_ms_15m: 180,
      slow_requests_15m: 1,
      server_errors_15m: 0,
      top_paths_15m: [
        {
          path: '/clubs',
          requests: 8,
          server_errors: 0,
          slow_requests: 1,
          avg_duration_ms: 90,
          p95_duration_ms: 180,
        },
      ],
    },
    clubsObservability: { summary: {}, hourly24h: [], daily14d: [], recentPressureWindows: [] },
    clearSnapshots: vi.fn(),
    data: {
      timestamp: '2026-04-13T06:00:00.000Z',
      db_status: 'healthy',
      uptime_seconds: 3600,
      error_count_24h: 2,
      active_sessions_24h: 14,
      slow_query_count_24h: 1,
      alert_count: 1,
      alerts: [{ code: 'db.latency', level: 'warning', message: 'Database latency is rising.' }],
      collection_counts: { users: 120, assignments: 40 },
      observability: {
        request_metrics: {
          requests_15m: 180,
          server_error_rate_pct_15m: 1.5,
          p95_duration_ms_15m: 220,
          slow_requests_15m: 3,
          top_paths_15m: [
            {
              path: '/admin/system/health',
              requests: 25,
              server_errors: 0,
              slow_requests: 1,
              avg_duration_ms: 110,
              p95_duration_ms: 220,
            },
          ],
        },
        scheduler_metrics: {
          runs_15m: 6,
          errors_15m: 1,
        },
      },
      scheduled_notice_dispatch: {
        pending_total: 4,
        due_now_total: 2,
        retry_pending_total: 1,
        oldest_due_age_seconds: 120,
      },
      scheduler: {
        status: 'running',
        last_heartbeat_at: '2026-04-13T05:58:00.000Z',
      },
      scheduler_lock: {
        owner: 'scheduler-1',
        expires_at: '2026-04-13T06:05:00.000Z',
      },
      snapshot_history: [{ bucket_minute: '2026-04-13T05:30:00.000Z' }],
      slow_query_logs: [
        {
          resource: 'users',
          detail: 'Slow scan on users collection',
          created_at: '2026-04-13T05:55:00.000Z',
        },
      ],
    },
    error: '',
    exportSnapshots: vi.fn(),
    historyData: [{ label: '05:45', queuedJobs: 4 }],
    isAutoRefresh: true,
    isRefreshing: false,
    loadHealth: vi.fn(),
    localHistoryData: [{ label: '05:45', queuedJobs: 4 }],
    localSnapshots: [{ timestamp: '2026-04-13T05:59:00.000Z' }],
    persistedHistoryData: [{ label: '05:30', queuedJobs: 4 }],
    setIsAutoRefresh: vi.fn(),
    snapshotStore: {
      retained_rows: 10,
      max_retained_rows: 100,
      retention_minutes: 180,
      is_within_retention_bound: true,
      last_pruned_deleted_count: 1,
      last_pruned_at: '2026-04-13T05:40:00.000Z',
      last_pruned_bucket: '2026-04-13T05:30:00.000Z',
    },
    ...overrides,
  };
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage(component) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(<MemoryRouter>{component}</MemoryRouter>);
    await waitForTick();
    await waitForTick();
  });
}

describe('Admin operations pages', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockUseAdminSystemHealth.mockReset();
    mockPushToast.mockReset();
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

  it('keeps the system page focused on overview and response content', async () => {
    await renderPage(<AdminSystemPage />);

    expect(document.body.textContent).toContain('Health Summary');
    expect(document.body.textContent).toContain('Active Alerts');
    expect(document.body.textContent).toContain('Traffic and Throughput');
    expect(document.body.textContent).toContain('AI and Scheduler Capacity');
    expect(document.body.textContent).toContain('Data and Storage Posture');
    expect(document.body.textContent).toContain('Recent Anomalies and Slow Queries');
    expect(document.body.textContent).toContain('Open deep observability');
    expect(document.body.textContent).toContain('Alert Routing History Mock');
    expect(document.body.textContent).not.toContain('System Health History Charts Mock');
    expect(document.body.textContent).not.toContain('Clubs Pressure Trends Mock');
  });

  it('keeps the observability page focused on diagnostics and trend analysis', async () => {
    await renderPage(<AdminObservabilityPage />);

    expect(document.body.textContent).toContain('Diagnostics Overview');
    expect(document.body.textContent).toContain('Historical Trends');
    expect(document.body.textContent).toContain('Clubs Diagnostics');
    expect(document.body.textContent).toContain('Endpoint Diagnostics');
    expect(document.body.textContent).toContain('Snapshot Retention');
    expect(document.body.textContent).toContain('Scheduler Detail');
    expect(document.body.textContent).toContain('Back to system overview');
    expect(document.body.textContent).toContain('System Health History Charts Mock');
    expect(document.body.textContent).toContain('Clubs Pressure Trends Mock');
    expect(document.body.textContent).not.toContain('Active Alerts');
    expect(document.body.textContent).not.toContain('Alert Routing History Mock');
  });

  it('keeps system overview visible when request metrics are missing', async () => {
    mockUseAdminSystemHealth.mockReturnValue(
      buildHookState({
        data: {
          ...buildHookState().data,
          observability: {
            request_metrics: {},
            scheduler_metrics: {
              runs_15m: 6,
              errors_15m: 1,
            },
          },
        },
      })
    );

    await renderPage(<AdminSystemPage />);

    expect(document.body.textContent).toContain('Health Summary');
    expect(document.body.textContent).toContain('No request metrics available in the latest health payload.');
  });

  it('shares canonical health status mapping across the operations surface', () => {
    expect(getHealthStatusMeta('healthy')).toEqual({ label: 'Healthy', variant: 'success' });
    expect(getHealthStatusMeta('degraded')).toEqual({ label: 'Warning', variant: 'warning' });
    expect(getHealthStatusMeta('critical')).toEqual({ label: 'Critical', variant: 'danger' });
    expect(getHealthStatusMeta(null)).toEqual({ label: 'Unknown', variant: 'default' });
  });
});
