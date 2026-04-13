// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminDashboardPage from './AdminDashboardPage';
import AdminDeveloperPage from './AdminDeveloperPage';

const {
  mockUseAuth,
  mockApiGet,
  mockFetchGovernanceDashboard,
  mockFetchGovernanceReviews,
  mockAdminDomainNav,
} = vi.hoisted(() => ({
  mockUseAuth: vi.fn(),
  mockApiGet: vi.fn(),
  mockFetchGovernanceDashboard: vi.fn(),
  mockFetchGovernanceReviews: vi.fn(),
  mockAdminDomainNav: vi.fn(() => <div data-testid="admin-domain-nav" />),
}));

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    get: mockApiGet,
  },
}));

vi.mock('../../services/adminGovernanceApi', () => ({
  fetchGovernanceDashboard: (...args) => mockFetchGovernanceDashboard(...args),
  fetchGovernanceReviews: (...args) => mockFetchGovernanceReviews(...args),
}));

vi.mock('../../components/admin/AdminDomainNav', () => ({
  default: (...args) => mockAdminDomainNav(...args),
}));

vi.mock('../../components/ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>,
}));

vi.mock('../../components/ui/Badge', () => ({
  default: ({ children }) => <span>{children}</span>,
}));

vi.mock('../../components/ui/EmptyState', () => ({
  default: ({ title, description }) => (
    <div>
      <p>{title}</p>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock('../../components/ui/Skeleton', () => ({
  default: ({ className = '' }) => <div className={className}>Loading</div>,
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function buildAdminUser(adminType = 'super_admin') {
  return {
    id: `admin-${adminType}`,
    full_name: 'Admin User',
    email: `${adminType}@caps.ai`,
    role: 'admin',
    admin_type: adminType,
  };
}

function mockDashboardApis({ analytics, system, governance, reviews }) {
  mockApiGet.mockImplementation((url) => {
    if (url === '/admin/analytics/bootstrap') {
      return analytics instanceof Error
        ? Promise.reject(analytics)
        : Promise.resolve({ data: { overview: analytics || {} } });
    }
    if (url === '/admin/system/health') {
      return system instanceof Error
        ? Promise.reject(system)
        : Promise.resolve({ data: system || {} });
    }
    return Promise.resolve({ data: {} });
  });

  mockFetchGovernanceDashboard.mockImplementation(() => {
    if (governance instanceof Error) {
      return Promise.reject(governance);
    }
    return Promise.resolve(governance || {});
  });

  mockFetchGovernanceReviews.mockImplementation(() => {
    if (reviews instanceof Error) {
      return Promise.reject(reviews);
    }
    return Promise.resolve(reviews || []);
  });
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage(component, { adminType = 'super_admin', route = '/admin/dashboard' } = {}) {
  mockUseAuth.mockReturnValue({
    user: buildAdminUser(adminType),
  });

  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(<MemoryRouter initialEntries={[route]}>{component}</MemoryRouter>);
    await waitForTick();
    await waitForTick();
  });
}

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockUseAuth.mockReset();
    mockApiGet.mockReset();
    mockFetchGovernanceDashboard.mockReset();
    mockFetchGovernanceReviews.mockReset();
    mockAdminDomainNav.mockReset();
    mockDashboardApis({
      analytics: {
        total_users: 120,
        active_students: 80,
        assignments_total: 45,
        active_clubs: 9,
      },
      system: {
        db_status: 'healthy',
        alert_count: 2,
        alerts: [
          { code: 'db.latency', level: 'warning', message: 'Database latency is rising.' },
        ],
      },
      governance: {
        pending_reviews: 3,
        locked_accounts: 1,
        login_anomalies_24h: 2,
        policy: {
          two_person_rule_enabled: true,
          role_change_approval_enabled: true,
        },
      },
      reviews: [
        {
          id: 'review-1',
          public_id: 'GR-001',
          status: 'pending',
          action: 'users.delete',
          entity_type: 'user',
          entity_label: 'User',
          requested_by_label: 'Alice',
          created_at: '2026-04-13T05:00:00.000Z',
        },
      ],
    });
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

  it('renders role-aware super admin actions and does not invoke the legacy chip navigation', async () => {
    await renderPage(<AdminDashboardPage />, { adminType: 'super_admin' });

    expect(document.body.textContent).toContain('Quick Actions');
    expect(document.body.textContent).toContain('Governance');
    expect(document.body.textContent).toContain('RBAC');
    expect(document.body.textContent).toContain('Audit Logs');
    expect(document.body.textContent).toContain('System Health');
    expect(document.body.textContent).toContain('Pending Approval Queue');
    expect(document.body.textContent).toContain('Operational Alerts');
    expect(mockAdminDomainNav).not.toHaveBeenCalled();
    expect(document.querySelector('[data-testid="admin-domain-nav"]')).toBeNull();
  });

  it('shows academic-admin actions while hiding governance and system-only panels', async () => {
    await renderPage(<AdminDashboardPage />, { adminType: 'academic_admin' });

    expect(document.body.textContent).toContain('Onboarding');
    expect(document.body.textContent).toContain('Students');
    expect(document.body.textContent).toContain('Academic Structure');
    expect(document.body.textContent).toContain('Analytics');
    expect(document.body.textContent).not.toContain('Pending Approval Queue');
    expect(document.body.textContent).not.toContain('Operational Alerts');
    expect(mockFetchGovernanceDashboard).not.toHaveBeenCalled();
    expect(mockFetchGovernanceReviews).not.toHaveBeenCalled();
    expect(mockApiGet).toHaveBeenCalledTimes(1);
    expect(mockApiGet).toHaveBeenCalledWith('/admin/analytics/bootstrap');
  });

  it('keeps the dashboard visible when one live source fails', async () => {
    mockDashboardApis({
      analytics: {
        total_users: 120,
        active_students: 80,
        assignments_total: 45,
        active_clubs: 9,
      },
      system: new Error('system unavailable'),
      governance: {
        pending_reviews: 3,
        locked_accounts: 1,
        login_anomalies_24h: 2,
        policy: {
          two_person_rule_enabled: true,
          role_change_approval_enabled: true,
        },
      },
      reviews: [],
    });

    await renderPage(<AdminDashboardPage />, { adminType: 'super_admin' });

    expect(document.body.textContent).toContain('Some live dashboard data is unavailable: system health.');
    expect(document.body.textContent).toContain('Platform Overview');
    expect(document.body.textContent).toContain('Pending Approval Queue');
    expect(document.body.textContent).toContain('No pending approvals');
  });

  it('keeps simple admin pages free of the legacy chip navigation too', async () => {
    await renderPage(<AdminDeveloperPage />, { adminType: 'super_admin', route: '/admin/developer' });

    expect(document.body.textContent).toContain('Developer Domain');
    expect(mockAdminDomainNav).not.toHaveBeenCalled();
    expect(document.querySelector('[data-testid="admin-domain-nav"]')).toBeNull();
  });
});
