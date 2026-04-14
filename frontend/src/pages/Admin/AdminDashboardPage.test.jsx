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

vi.mock('../../components/ui/InlineErrorState', () => ({
  default: ({ title, description }) => (
    <div>
      <p>{title}</p>
      <p>{description}</p>
    </div>
  ),
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

function mockDashboardData({
  analytics,
  system,
  governance,
  reviews,
  auditLogs,
  onboarding,
}) {
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
    if (url === '/audit-logs/') {
      return auditLogs instanceof Error
        ? Promise.reject(auditLogs)
        : Promise.resolve({ data: auditLogs || [] });
    }
    if (url === '/admin/analytics/overview') {
      return onboarding instanceof Error
        ? Promise.reject(onboarding)
        : Promise.resolve({ data: onboarding || null });
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
    mockDashboardData({
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
      auditLogs: [
        {
          id: 'audit-1',
          action: 'restore',
          entity_type: 'notices',
          resource_type: 'notices',
          entity_label: 'Semester Notice',
          actor_label: 'Alice Admin',
          created_at: '2026-04-13T05:30:00.000Z',
        },
        {
          id: 'audit-2',
          action: 'rbac_role_updated',
          entity_type: 'admin_user',
          resource_type: 'admin_user',
          entity_label: 'Bob Admin',
          actor_label: 'Alice Admin',
          created_at: '2026-04-13T05:20:00.000Z',
        },
        {
          id: 'audit-3',
          action: 'governance.approved',
          entity_type: 'governance_review',
          resource_type: 'governance_review',
          entity_label: 'GR-204',
          actor_label: 'Risk Reviewer',
          created_at: '2026-04-13T05:10:00.000Z',
        },
        {
          id: 'audit-4',
          action: 'session.revoked',
          entity_type: 'user_session',
          resource_type: 'user_session',
          entity_label: 'Session 44',
          actor_label: 'Security Admin',
          created_at: '2026-04-13T05:05:00.000Z',
        },
      ],
      onboarding: {
        progress: {
          completed_steps: 3,
          total_steps: 5,
          percent: 60,
        },
        next_step: {
          label: 'Create Departments',
          description: 'Set up the first academic departments.',
          action_path: '/academic-structure',
          cta_label: 'Open Academic Structure',
        },
        steps: [
          { key: 'university', label: 'Create University', is_complete: true, description: 'University created.' },
          { key: 'campus', label: 'Create Campus', is_complete: true, description: 'Campus created.' },
          { key: 'program', label: 'Create Program', is_complete: true, description: 'Program created.' },
        ],
      },
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
    expect(document.body.textContent).toContain('Recent Activity');
    expect(document.body.textContent).toContain('Action Outcomes');
    expect(document.body.textContent).toContain('Restore completed');
    expect(document.body.textContent).toContain('Access change recorded');
    expect(mockAdminDomainNav).not.toHaveBeenCalled();
    expect(document.querySelector('[data-testid="admin-domain-nav"]')).toBeNull();
    const links = Array.from(document.querySelectorAll('a')).map((link) => link.getAttribute('href'));
    expect(links).toContain('/audit-logs?action=restore&entity_type=notices&resource_type=notices');
  });

  it('shows academic-admin actions while hiding governance and system-only panels', async () => {
    await renderPage(<AdminDashboardPage />, { adminType: 'academic_admin' });

    expect(document.body.textContent).toContain('Onboarding');
    expect(document.body.textContent).toContain('Students');
    expect(document.body.textContent).toContain('Academic Structure');
    expect(document.body.textContent).toContain('Analytics');
    expect(document.body.textContent).toContain('Steps Complete');
    expect(document.body.textContent).toContain('Create Departments');
    expect(document.body.textContent).toContain('Latest completed milestone');
    expect(document.body.textContent).toContain('Create Program');
    expect(document.body.textContent).not.toContain('Pending Approval Queue');
    expect(document.body.textContent).not.toContain('Operational Alerts');
    expect(document.body.textContent).not.toContain('Open Audit Logs');
    expect(mockFetchGovernanceDashboard).not.toHaveBeenCalled();
    expect(mockFetchGovernanceReviews).not.toHaveBeenCalled();
    expect(mockApiGet).toHaveBeenCalledTimes(2);
    expect(mockApiGet).toHaveBeenCalledWith('/admin/analytics/bootstrap');
    expect(mockApiGet).toHaveBeenCalledWith('/admin/analytics/overview');
  });

  it('keeps the dashboard visible when one live source fails', async () => {
    mockDashboardData({
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
      auditLogs: [
        {
          id: 'audit-1',
          action: 'restore',
          entity_type: 'notices',
          resource_type: 'notices',
          entity_label: 'Semester Notice',
          actor_label: 'Alice Admin',
          created_at: '2026-04-13T05:30:00.000Z',
        },
      ],
    });

    await renderPage(<AdminDashboardPage />, { adminType: 'super_admin' });

    expect(document.body.textContent).toContain('Some live dashboard data is unavailable: system health.');
    expect(document.body.textContent).toContain('Platform Overview');
    expect(document.body.textContent).toContain('Pending Approval Queue');
    expect(document.body.textContent).toContain('No pending approvals');
  });

  it('keeps the dashboard visible when the recent activity source fails', async () => {
    mockDashboardData({
      analytics: {
        total_users: 120,
        active_students: 80,
        assignments_total: 45,
        active_clubs: 9,
      },
      system: {
        db_status: 'healthy',
        alert_count: 0,
        alerts: [],
      },
      governance: {
        pending_reviews: 0,
        locked_accounts: 0,
        login_anomalies_24h: 0,
        policy: {
          two_person_rule_enabled: true,
          role_change_approval_enabled: true,
        },
      },
      reviews: [],
      auditLogs: new Error('audit unavailable'),
    });

    await renderPage(<AdminDashboardPage />, { adminType: 'admin' });

    expect(document.body.textContent).toContain('Recent activity unavailable');
    expect(document.body.textContent).toContain('Action outcomes unavailable');
    expect(document.body.textContent).toContain('Platform Overview');
    expect(document.body.textContent).not.toContain('RBAC');
  });

  it('shows readable empty states when there is no recent audit activity', async () => {
    mockDashboardData({
      analytics: {
        total_users: 120,
        active_students: 80,
        assignments_total: 45,
        active_clubs: 9,
      },
      system: {
        db_status: 'healthy',
        alert_count: 0,
        alerts: [],
      },
      governance: {},
      reviews: [],
      auditLogs: [],
    });

    await renderPage(<AdminDashboardPage />, { adminType: 'compliance_admin' });

    expect(document.body.textContent).toContain('No recent admin activity yet');
    expect(document.body.textContent).toContain('No action outcomes yet');
    expect(document.body.textContent).toContain('Open Audit Logs');
  });

  it('keeps simple admin pages free of the legacy chip navigation too', async () => {
    await renderPage(<AdminDeveloperPage />, { adminType: 'super_admin', route: '/admin/developer' });

    expect(document.body.textContent).toContain('Developer Domain');
    expect(mockAdminDomainNav).not.toHaveBeenCalled();
    expect(document.querySelector('[data-testid="admin-domain-nav"]')).toBeNull();
  });
});
