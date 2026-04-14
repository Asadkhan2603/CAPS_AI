// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminRbacPage from './AdminRbacPage';
import AdminGovernancePage from './AdminGovernancePage';
import AuditLogsPage from '../AuditLogsPage';

const {
  mockPushToast,
  mockApiGet,
  mockFetchRbacDesign,
  mockFetchRbacPermissions,
  mockFetchRbacRoles,
  mockFetchAdminUsers,
  mockFetchAdminUser,
  mockCreateAdminUser,
  mockUpdateAdminUser,
  mockUpdateAdminUserStatus,
  mockDeleteAdminUser,
  mockCreateRbacRole,
  mockUpdateRbacRole,
  mockDeleteRbacRole,
  mockFetchGovernanceDashboard,
  mockFetchGovernancePolicy,
  mockFetchGovernanceReviews,
  mockFetchGovernanceSessions,
  mockCreateGovernanceReview,
  mockDecideGovernanceReview,
  mockUpdateGovernancePolicy,
  mockEntityManager,
  mockTable,
} = vi.hoisted(() => ({
  mockPushToast: vi.fn(),
  mockApiGet: vi.fn(),
  mockFetchRbacDesign: vi.fn(),
  mockFetchRbacPermissions: vi.fn(),
  mockFetchRbacRoles: vi.fn(),
  mockFetchAdminUsers: vi.fn(),
  mockFetchAdminUser: vi.fn(),
  mockCreateAdminUser: vi.fn(),
  mockUpdateAdminUser: vi.fn(),
  mockUpdateAdminUserStatus: vi.fn(),
  mockDeleteAdminUser: vi.fn(),
  mockCreateRbacRole: vi.fn(),
  mockUpdateRbacRole: vi.fn(),
  mockDeleteRbacRole: vi.fn(),
  mockFetchGovernanceDashboard: vi.fn(),
  mockFetchGovernancePolicy: vi.fn(),
  mockFetchGovernanceReviews: vi.fn(),
  mockFetchGovernanceSessions: vi.fn(),
  mockCreateGovernanceReview: vi.fn(),
  mockDecideGovernanceReview: vi.fn(),
  mockUpdateGovernancePolicy: vi.fn(),
  mockEntityManager: vi.fn((props) => <div data-testid="entity-manager">{JSON.stringify(props.filters)}</div>),
  mockTable: vi.fn(({ columns, data, rowActions = [] }) => (
    <div>
      {data.map((row, index) => (
        <div key={row.id || index} data-testid="table-row">
          {columns.map((column) => (
            <div key={column.key}>
              {column.render ? column.render(row) : row[column.key] ?? '-'}
            </div>
          ))}
          <div>
            {rowActions.map((action) => (
              <button
                key={action.key}
                type="button"
                disabled={typeof action.disabled === 'function' ? action.disabled(row) : action.disabled}
                onClick={() => action.onClick(row)}
              >
                {typeof action.label === 'function' ? action.label(row) : action.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )),
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({ pushToast: mockPushToast }),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    get: (...args) => mockApiGet(...args),
  },
}));

vi.mock('../../services/adminRbacApi', () => ({
  createAdminUser: (...args) => mockCreateAdminUser(...args),
  createRbacRole: (...args) => mockCreateRbacRole(...args),
  deleteAdminUser: (...args) => mockDeleteAdminUser(...args),
  deleteRbacRole: (...args) => mockDeleteRbacRole(...args),
  fetchAdminUser: (...args) => mockFetchAdminUser(...args),
  fetchAdminUsers: (...args) => mockFetchAdminUsers(...args),
  fetchRbacDesign: (...args) => mockFetchRbacDesign(...args),
  fetchRbacPermissions: (...args) => mockFetchRbacPermissions(...args),
  fetchRbacRoles: (...args) => mockFetchRbacRoles(...args),
  updateAdminUser: (...args) => mockUpdateAdminUser(...args),
  updateAdminUserStatus: (...args) => mockUpdateAdminUserStatus(...args),
  updateRbacRole: (...args) => mockUpdateRbacRole(...args),
}));

vi.mock('../../services/adminGovernanceApi', () => ({
  createGovernanceReview: (...args) => mockCreateGovernanceReview(...args),
  decideGovernanceReview: (...args) => mockDecideGovernanceReview(...args),
  fetchGovernanceDashboard: (...args) => mockFetchGovernanceDashboard(...args),
  fetchGovernancePolicy: (...args) => mockFetchGovernancePolicy(...args),
  fetchGovernanceReviews: (...args) => mockFetchGovernanceReviews(...args),
  fetchGovernanceSessions: (...args) => mockFetchGovernanceSessions(...args),
  updateGovernancePolicy: (...args) => mockUpdateGovernancePolicy(...args),
}));

vi.mock('../../components/ui/EntityManager', () => ({
  default: (...args) => mockEntityManager(...args),
}));

vi.mock('../../components/ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>,
}));

vi.mock('../../components/ui/EmptyState', () => ({
  default: ({ title, description }) => (
    <div>
      <p>{title}</p>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock('../../components/ui/Modal', () => ({
  default: ({ open, children }) => (open ? <div>{children}</div> : null),
}));

vi.mock('../../components/ui/FormInput', () => ({
  default: ({ as = 'input', label, children, ...props }) => {
    if (as === 'select') {
      return (
        <label>
          <span>{label}</span>
          <select {...props}>{children}</select>
        </label>
      );
    }

    return (
      <label>
        <span>{label}</span>
        <input {...props} />
      </label>
    );
  },
}));

vi.mock('../../components/ui/Table', () => ({
  default: (...args) => mockTable(...args),
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
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

async function clickButton(label) {
  const button = Array.from(document.querySelectorAll('button')).find((item) => item.textContent?.includes(label));
  expect(button).toBeTruthy();
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await waitForTick();
    await waitForTick();
  });
}

function getLinks() {
  return Array.from(document.querySelectorAll('a')).map((link) => ({
    text: link.textContent || '',
    href: link.getAttribute('href') || '',
  }));
}

describe('Admin access and compliance workflow handoffs', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockPushToast.mockReset();
    mockApiGet.mockReset();
    mockFetchRbacDesign.mockReset();
    mockFetchRbacPermissions.mockReset();
    mockFetchRbacRoles.mockReset();
    mockFetchAdminUsers.mockReset();
    mockFetchAdminUser.mockReset();
    mockCreateAdminUser.mockReset();
    mockUpdateAdminUser.mockReset();
    mockUpdateAdminUserStatus.mockReset();
    mockDeleteAdminUser.mockReset();
    mockCreateRbacRole.mockReset();
    mockUpdateRbacRole.mockReset();
    mockDeleteRbacRole.mockReset();
    mockFetchGovernanceDashboard.mockReset();
    mockFetchGovernancePolicy.mockReset();
    mockFetchGovernanceReviews.mockReset();
    mockFetchGovernanceSessions.mockReset();
    mockCreateGovernanceReview.mockReset();
    mockDecideGovernanceReview.mockReset();
    mockUpdateGovernancePolicy.mockReset();
    mockEntityManager.mockClear();
    mockTable.mockClear();

    mockFetchRbacDesign.mockResolvedValue({
      roles: [{ code: 'SUPER_ADMIN', name: 'Super Admin', description: 'System owner', permissions: [], scope_required: false }],
      permission_groups: [],
      scope_fields: ['department_id', 'year_id'],
    });
    mockFetchRbacPermissions.mockResolvedValue([
      { key: 'users.manage', module_key: 'users', module: 'Users', description: 'Manage users' },
    ]);
    mockFetchRbacRoles.mockResolvedValue([
      { id: 'role-1', code: 'REPORT_REVIEWER', name: 'Report Reviewer', description: 'Review reports', permission_keys: [], is_system: false, is_active: true },
    ]);
    mockFetchAdminUsers.mockResolvedValue([
      {
        id: 'admin-1',
        full_name: 'Alice Admin',
        email: 'alice@caps.ai',
        admin_role: { code: 'REPORT_REVIEWER', name: 'Report Reviewer' },
        rbac_role_code: 'REPORT_REVIEWER',
        status: 'active',
        is_active: true,
        scopes: [],
        permissions: [],
        permission_overrides: { allow_permission_keys: [], deny_permission_keys: [] },
        created_at: '2026-04-13T05:00:00.000Z',
        updated_at: '2026-04-13T05:10:00.000Z',
      },
    ]);
    mockUpdateAdminUserStatus.mockResolvedValue({ success: true });
    mockApiGet.mockResolvedValue({
      data: [
        {
          id: 'audit-1',
          entity_type: 'admin_user',
          resource_type: 'admin_user',
          action_type: 'rbac_role_updated',
          detail: 'Role updated',
          actor_user_id: 'admin-1',
          created_at: '2026-04-13T05:15:00.000Z',
        },
      ],
    });

    mockFetchGovernancePolicy.mockResolvedValue({
      two_person_rule_enabled: true,
      role_change_approval_enabled: true,
      retention_days_audit: 365,
      retention_days_sessions: 90,
    });
    mockFetchGovernanceDashboard.mockResolvedValue({
      pending_reviews: 2,
      approved_reviews_24h: 5,
      login_anomalies_24h: 1,
      locked_accounts: 0,
    });
    mockFetchGovernanceReviews.mockResolvedValue([
      {
        id: 'review-role',
        public_id: 'GR-001',
        review_type: 'role_change',
        action: 'rbac.assign_role',
        entity_type: 'admin_user',
        entity_label: 'Alice Admin',
        status: 'pending',
        requested_by_label: 'System',
        created_at: '2026-04-13T05:20:00.000Z',
      },
      {
        id: 'review-delete',
        public_id: 'GR-002',
        review_type: 'destructive',
        action: 'users.delete',
        entity_type: 'user',
        entity_label: 'Student Record',
        status: 'pending',
        requested_by_label: 'System',
        created_at: '2026-04-13T05:25:00.000Z',
      },
    ]);
    mockFetchGovernanceSessions.mockResolvedValue({
      items: [
        {
          id: 'session-1',
          user_label: 'Alice Admin',
          status: 'active',
          ip_address: '127.0.0.1',
          fingerprint: 'abcdef1234567890',
          last_seen_at: '2026-04-13T05:40:00.000Z',
        },
      ],
    });
    mockUpdateGovernancePolicy.mockImplementation(async (payload) => payload);
    mockDecideGovernanceReview.mockResolvedValue({ success: true });
    mockCreateGovernanceReview.mockResolvedValue({ success: true });
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

  it('shows RBAC related actions, a success handoff after mutations, and drill-down audit links', async () => {
    await renderPage(<AdminRbacPage />, '/admin/rbac');

    expect(document.body.textContent).toContain('Related Actions');
    let links = getLinks();
    expect(links.some((link) => link.href === '/admin/governance?context=rbac_follow_up')).toBe(true);
    expect(links.some((link) => link.href === '/audit-logs?resource_type=admin_user')).toBe(true);
    expect(links.some((link) => link.href.includes('/audit-logs?resource_type=admin_user&entity_type=admin_user&action=rbac_role_updated&actor_user_id=admin-1'))).toBe(true);

    await clickButton('Toggle Status');

    expect(mockUpdateAdminUserStatus).toHaveBeenCalledWith('admin-1', { is_active: false });
    expect(document.body.textContent).toContain('Admin deactivated');
    expect(mockTable.mock.calls.some((call) => call[0]?.responsive === true)).toBe(true);
    links = getLinks();
    expect(links.some((link) => link.href === '/admin/governance?context=rbac_follow_up')).toBe(true);
    expect(links.some((link) => link.href === '/audit-logs?resource_type=admin_user&entity_type=admin_user&action=status_update')).toBe(true);
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Admin deactivated',
        variant: 'success',
      })
    );
  });

  it('shows governance follow-up links for review rows, session rows, and result states', async () => {
    await renderPage(<AdminGovernancePage />, '/admin/governance');

    expect(document.body.textContent).toContain('Related Actions');
    let links = getLinks();
    expect(links.some((link) => link.href === '/admin/rbac?context=governance_follow_up')).toBe(true);
    expect(links.some((link) => link.href === '/admin/rbac?context=role_change')).toBe(true);
    expect(links.some((link) => link.href === '/audit-logs?action=users.delete&entity_type=user&resource_type=user')).toBe(true);
    expect(links.some((link) => link.href === '/audit-logs?entity_type=user_session&resource_type=user_session')).toBe(true);

    await clickButton('Save Policy');

    expect(document.body.textContent).toContain('Policy saved');
    expect(mockTable.mock.calls.some((call) => call[0]?.responsive === true && call[0]?.stickyActions === true)).toBe(true);
    links = getLinks();
    expect(
      links.some(
        (link) =>
          link.href.startsWith('/audit-logs?')
          && link.href.includes('action=update')
          && link.href.includes('entity_type=governance_policy')
          && link.href.includes('resource_type=governance_policy')
      )
    ).toBe(true);

    await clickButton('Approve');

    expect(mockDecideGovernanceReview).toHaveBeenCalledWith('review-role', { approve: true, note: 'Approved in admin panel' });
    expect(document.body.textContent).toContain('Review approved');
    links = getLinks();
    expect(links.some((link) => link.href === '/admin/rbac?context=role_change')).toBe(true);
    expect(
      links.some(
        (link) =>
          link.href.startsWith('/audit-logs?')
          && link.href.includes('action=rbac.assign_role')
          && link.href.includes('entity_type=admin_user')
          && link.href.includes('resource_type=admin_user')
      )
    ).toBe(true);
  });

  it('keeps audit-log prefills stable for shared handoff query parameters', async () => {
    await renderPage(<AuditLogsPage />, '/audit-logs?action=restore&resource_type=notices&entity_type=notices');

    expect(mockEntityManager).toHaveBeenCalled();
    const lastCall = mockEntityManager.mock.calls.at(-1)?.[0];
    expect(lastCall.endpoint).toBe('/audit-logs/');
    expect(lastCall.filters).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: 'action', defaultValue: 'restore' }),
        expect.objectContaining({ name: 'resource_type', defaultValue: 'notices' }),
        expect.objectContaining({ name: 'entity_type', defaultValue: 'notices' }),
      ])
    );
  });
});
