// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import NotificationsPage from './NotificationsPage';

const { mockPushToast, mockUseAuth, mockApiGet, mockApiPatch, mockApiPost } = vi.hoisted(() => ({
  mockPushToast: vi.fn(),
  mockUseAuth: vi.fn(),
  mockApiGet: vi.fn(),
  mockApiPatch: vi.fn(),
  mockApiPost: vi.fn()
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: mockPushToast
  })
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    get: mockApiGet,
    patch: mockApiPatch,
    post: mockApiPost
  }
}));

vi.mock('../components/communication/CommunicationTabs', () => ({
  default: () => <div data-testid="communication-tabs" />
}));

vi.mock('../components/communication/CommunicationDeliveryModal', () => ({
  default: () => null
}));

vi.mock('../components/ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>
}));

vi.mock('../components/ui/Badge', () => ({
  default: ({ children }) => <span>{children}</span>
}));

vi.mock('../components/ui/FormInput', () => ({
  default: ({ label, as = 'input', children, ...props }) => {
    const Component = as;
    return (
      <label>
        {label ? <span>{label}</span> : null}
        <Component {...props}>{children}</Component>
      </label>
    );
  }
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;
const mockScrollIntoView = vi.fn();

function buildUser(role, overrides = {}) {
  return {
    id: `${role}-1`,
    full_name: `${role} user`,
    email: `${role}@caps.ai`,
    role,
    communication_preferences: {},
    ...overrides
  };
}

function mockGetImplementation() {
  mockApiGet.mockImplementation((url) => {
    if (url === '/notifications/') {
      return Promise.resolve({ data: [] });
    }
    if (url === '/users/') {
      return Promise.resolve({ data: [] });
    }
    if (url === '/admin/communication/delivery/report') {
      return Promise.resolve({ data: {} });
    }
    if (url === '/admin/communication/delivery/report/benchmarks') {
      return Promise.resolve({ data: { metrics: [] } });
    }
    if (url === '/admin/communication/delivery/incidents') {
      return Promise.resolve({ data: { incidents: [] } });
    }
    return Promise.resolve({ data: {} });
  });
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function findLabeledControl(labelText, selector = 'select') {
  const label = Array.from(document.querySelectorAll('label')).find((item) => item.textContent?.includes(labelText));
  return label?.querySelector(selector) || null;
}

async function renderPage(role = 'admin', overrides = {}) {
  mockUseAuth.mockReturnValue({
    user: buildUser(role, overrides),
    refreshUser: vi.fn()
  });

  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={['/workspace/communication/notifications']}>
        <NotificationsPage />
      </MemoryRouter>
    );
    await waitForTick();
    await waitForTick();
  });
}

async function clickButton(label) {
  const button = document.querySelector(`button[aria-label="${label}"]`);
  expect(button).not.toBeNull();
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await waitForTick();
  });
}

describe('NotificationsPage banner actions', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: mockScrollIntoView
    });
    window.history.replaceState(null, '', '/workspace/communication/notifications');
    mockScrollIntoView.mockReset();
    mockPushToast.mockReset();
    mockUseAuth.mockReset();
    mockApiGet.mockReset();
    mockApiPatch.mockReset();
    mockApiPost.mockReset();
    mockGetImplementation();
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

  it('routes banner buttons to the relevant sections for creators', async () => {
    await renderPage('admin');

    await clickButton('Notification settings');
    expect(window.location.hash).toBe('#notification-preferences');
    expect(document.getElementById('notification-preferences')).toBe(document.activeElement);

    await clickButton('FILTER');
    expect(window.location.hash).toBe('#notification-filters');
    expect(document.getElementById('notification-filters')).toBe(document.activeElement);

    await clickButton('CREATE');
    expect(window.location.hash).toBe('#notification-create');
    expect(document.getElementById('notification-create')).toBe(document.activeElement);
    expect(mockScrollIntoView).toHaveBeenCalledTimes(3);
    expect(mockPushToast).not.toHaveBeenCalled();
  });

  it('hides the create banner button for non-creator roles', async () => {
    await renderPage('student');

    expect(document.querySelector('button[aria-label="Notification settings"]')).not.toBeNull();
    expect(document.querySelector('button[aria-label="FILTER"]')).not.toBeNull();
    expect(document.querySelector('button[aria-label="CREATE"]')).toBeNull();
  });

  it('does not load operator-only reporting endpoints for teachers without communication extensions', async () => {
    await renderPage('teacher', { extended_roles: [] });

    expect(mockApiGet).toHaveBeenCalledWith('/notifications/', { params: { skip: 0, limit: 20 } });
    expect(mockApiGet).not.toHaveBeenCalledWith('/users/');
    expect(mockApiGet).not.toHaveBeenCalledWith(
      '/admin/communication/delivery/report',
      expect.anything()
    );
    expect(mockApiGet).not.toHaveBeenCalledWith(
      '/admin/communication/delivery/report/trends',
      expect.anything()
    );
    expect(mockApiGet).not.toHaveBeenCalledWith(
      '/admin/communication/delivery/report/anomalies',
      expect.anything()
    );
    expect(mockApiGet).not.toHaveBeenCalledWith(
      '/admin/communication/delivery/report/benchmarks',
      expect.anything()
    );
    expect(mockApiGet).not.toHaveBeenCalledWith(
      '/admin/communication/delivery/incidents',
      expect.anything()
    );
    expect(mockPushToast).not.toHaveBeenCalled();
  });

  it('lets operators jump from benchmarks and incidents into focused reconciliation views', async () => {
    mockApiGet.mockImplementation((url) => {
      if (url === '/notifications/') {
        return Promise.resolve({ data: [] });
      }
      if (url === '/users/') {
        return Promise.resolve({ data: [] });
      }
      if (url === '/admin/communication/delivery/report') {
        return Promise.resolve({ data: {} });
      }
      if (url === '/admin/communication/delivery/report/benchmarks') {
        return Promise.resolve({
          data: {
            current_start: '2026-04-05T00:00:00Z',
            current_end: '2026-04-12T00:00:00Z',
            metrics: [
              {
                key: 'failed_count',
                label: 'Failed Count',
                current_value: 8,
                previous_value: 3,
                delta_value: 5,
                delta_pct: 166.7,
                trend: 'up'
              }
            ]
          }
        });
      }
      if (url === '/admin/communication/delivery/incidents') {
        return Promise.resolve({
          data: {
            incidents: [
              {
                alert_code: 'delivery.pending_buildup',
                level: 'warning',
                message: 'Pending backlog rising.',
                is_active: true,
                last_seen_at: '2026-04-12T08:00:00Z',
                routed_count: 1,
                resolved_count: 0,
                cooldown_suppressed_count: 0,
                notifications_sent_total: 1,
                history: []
              }
            ]
          }
        });
      }
      return Promise.resolve({ data: {} });
    });

    await renderPage('admin');

    const statusFilter = findLabeledControl('Status Filter');
    expect(statusFilter).not.toBeNull();
    expect(statusFilter.value).toBe('');

    await clickButton('Focus benchmark rows for Failed Count');
    await act(async () => {
      await waitForTick();
      await waitForTick();
    });
    expect(statusFilter.value).toBe('failed');

    await clickButton('Focus impacted rows for delivery.pending_buildup');
    await act(async () => {
      await waitForTick();
      await waitForTick();
    });
    expect(statusFilter.value).toBe('pending');
    expect(mockScrollIntoView).toHaveBeenCalled();
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Report view updated',
        variant: 'info'
      })
    );
  });
});
