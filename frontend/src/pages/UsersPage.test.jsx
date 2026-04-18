// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import UsersPage from './UsersPage';

const { mockPushToast, mockUseUsersPageData } = vi.hoisted(() => ({
  mockPushToast: vi.fn(),
  mockUseUsersPageData: vi.fn()
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: mockPushToast
  })
}));

vi.mock('../hooks/useAuthorizedImage', () => ({
  useAuthorizedImage: () => null
}));

vi.mock('./users/UserDetailOverlay', () => ({
  default: ({ selectedUser }) => (
    <div data-testid="user-detail-overlay">{selectedUser ? selectedUser.full_name : 'none'}</div>
  )
}));

vi.mock('./users/useUsersPageData', () => ({
  useUsersPageData: (args) => mockUseUsersPageData(args)
}));

vi.mock('../components/ui/Table', () => ({
  default: ({ data = [], onToggleRow, onToggleAllRows, selectedRowIds = [], rowActions = [], onRowClick, rowClassName }) => (
    <div data-testid="users-table">
      <button type="button" aria-label="toggle-all" onClick={onToggleAllRows}>Toggle All</button>
      {data.map((row) => (
        <div key={row.id} data-testid={`row-${row.id}`} data-row-class={typeof rowClassName === 'function' ? rowClassName(row) : rowClassName}>
          <button type="button" aria-label={`open-row-${row.id}`} onClick={() => onRowClick?.(row)}>
            {row.full_name}
          </button>
          <span>{selectedRowIds.includes(row.id) ? 'selected' : 'not-selected'}</span>
          <button type="button" aria-label={`toggle-${row.id}`} onClick={() => onToggleRow?.(row)}>
            Toggle Row
          </button>
          {rowActions.map((action) => {
            const hidden = typeof action.hidden === 'function' ? action.hidden(row) : Boolean(action.hidden);
            if (hidden) return null;
            const label = typeof action.label === 'function' ? action.label(row) : action.label;
            const disabled = typeof action.disabled === 'function' ? action.disabled(row) : Boolean(action.disabled);
            return (
              <button
                key={`${row.id}-${action.key}`}
                type="button"
                aria-label={`${action.key}-${row.id}`}
                disabled={disabled}
                onClick={() => action.onClick?.(row)}
              >
                {label}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  )
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function buildHookData(overrides = {}) {
  const userRow = {
    id: 'user-1',
    full_name: 'Alice Admin',
    email: 'alice.admin@example.com',
    role: 'teacher',
    admin_type: null,
    is_active: true,
    extended_roles: [],
    department: 'Engineering',
    designation: 'Lecturer'
  };
  return {
    capabilities: {
      workspace: true,
      activity: true,
      bulk_operations: true,
      permission_templates: true,
      invitations: true,
      import_export: true,
      inline_editing: true,
      compact_density: true,
      responsive_workflows: true,
      rollout_stage: 'all_admins',
      rollout_cohort: 'admin',
      rollout_access: true,
      rollout_reason: null
    },
    adminDashboard: {
      latency: { request_count: 10, p95_duration_ms: 220, p99_duration_ms: 300, error_rate_pct: 0.5 },
      pagination: { sample_count: 10, empty_page_rate_pct: 1.0, deep_page_rate_pct: 5.0, top_page_sizes: [] }
    },
    adminDashboardLoading: false,
    adminDashboardError: '',
    loadAdminDashboard: vi.fn(),
    rows: [userRow],
    meta: { page: 1, limit: 25, total: 1, total_pages: 1 },
    loading: false,
    error: '',
    filterOptions: {
      roles: [{ value: 'teacher', count: 1 }],
      admin_types: [],
      extensions: [],
      departments: [{ value: 'Engineering', count: 1 }],
      status: [{ value: 'active', count: 1 }]
    },
    filtersLoading: false,
    getMergedUserById: (id) => (id === userRow.id ? userRow : null),
    loadUserActivity: vi.fn(),
    activityByUserId: {},
    activityLoadingByUserId: {},
    getEffectiveExtensions: () => [],
    getEffectiveScope: () => ({}),
    toggleExtension: vi.fn(),
    updateClassCoordinatorScope: vi.fn(),
    updateClubPresidentScope: vi.fn(),
    updateClassRepresentativeScope: vi.fn(),
    applyPermissionTemplate: vi.fn(),
    savePermissions: vi.fn(),
    resetPermissionDraft: vi.fn(),
    savingIds: [],
    updatingProfileIds: [],
    updateUserProfile: vi.fn(),
    updateUserStatus: vi.fn(),
    bulkUpdateStatus: vi.fn().mockResolvedValue({ updated_count: 1, failed_count: 0, results: [] }),
    bulkUpdateExtensions: vi.fn().mockResolvedValue({ updated_count: 1, failed_count: 0, results: [] }),
    refreshUsers: vi.fn(),
    createDirectUser: vi.fn(),
    creatingUser: false,
    inviteUser: vi.fn(),
    invitingUser: false,
    previewImport: vi.fn(),
    importPreview: null,
    commitImport: vi.fn(),
    importing: false,
    setImportPreview: vi.fn(),
    exportCsv: vi.fn(),
    filterPresets: [],
    filterPresetsLoading: false,
    savingFilterPreset: false,
    createFilterPreset: vi.fn(),
    updateFilterPreset: vi.fn(),
    deleteFilterPreset: vi.fn(),
    permissionTemplates: [],
    permissionTemplateSaving: false,
    createPermissionTemplate: vi.fn(),
    updatePermissionTemplate: vi.fn(),
    deletePermissionTemplate: vi.fn(),
    faculties: [],
    departments: [],
    programs: [],
    specializations: [],
    batches: [],
    semesters: [],
    sections: [],
    clubs: [],
    ...overrides
  };
}

async function renderPage(initialEntry = '/workspace/administration/users') {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <UsersPage />
      </MemoryRouter>
    );
    await waitForTick();
    await waitForTick();
  });
}

describe('UsersPage workspace and filters', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockPushToast.mockReset();
    mockUseUsersPageData.mockReset();
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

  it('renders users workspace with filter chips and table rows', async () => {
    mockUseUsersPageData.mockReturnValue(buildHookData());

    await renderPage('/workspace/administration/users?role=teacher&status=active');

    expect(document.body.textContent).toContain('Admin Users Workspace');
    expect(document.body.textContent).toContain('Role: teacher');
    expect(document.body.textContent).toContain('Status: active');
    expect(document.body.textContent).toContain('1 users found');
    expect(document.body.textContent).toContain('Alice Admin');
    expect(document.querySelector('[data-testid="users-table"]')).not.toBeNull();
  });

  it('shows rollout reason when workspace capability is disabled', async () => {
    mockUseUsersPageData.mockReturnValue(
      buildHookData({
        capabilities: {
          workspace: false,
          activity: true,
          bulk_operations: true,
          permission_templates: true,
          invitations: true,
          import_export: true,
          inline_editing: true,
          compact_density: true,
          responsive_workflows: true,
          rollout_stage: 'super_admins',
          rollout_cohort: 'admin',
          rollout_access: false,
          rollout_reason: 'Users admin rollout is currently limited to super admins.'
        }
      })
    );

    await renderPage('/workspace/administration/users');

    expect(document.body.textContent).toContain('Users admin rollout is currently limited to super admins.');
    expect(document.body.textContent).toContain('Current rollout stage: super admins.');
  });

  it('shows sticky bulk toolbar after selecting a row', async () => {
    mockUseUsersPageData.mockReturnValue(buildHookData());
    await renderPage('/workspace/administration/users');

    const toggleButton = document.querySelector('button[aria-label="toggle-user-1"]');
    expect(toggleButton).not.toBeNull();

    await act(async () => {
      toggleButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(document.body.textContent).toContain('1 user(s) selected');
    expect(document.body.textContent).toContain('Apply Extension');
    expect(document.body.textContent).toContain('Clear Selection');
  });

  it('uses row click + quick actions without duplicate open/status mutations', async () => {
    mockUseUsersPageData.mockReturnValue(buildHookData());
    await renderPage('/workspace/administration/users');

    const openButton = Array.from(document.querySelectorAll('button')).find(
      (item) => item.textContent?.trim() === 'Open'
    );
    expect(openButton).toBeUndefined();

    const openRiskButton = Array.from(document.querySelectorAll('button')).find(
      (item) => item.textContent?.trim() === 'Open Risk'
    );
    expect(openRiskButton).not.toBeNull();

    const activateButton = Array.from(document.querySelectorAll('button')).find(
      (item) => item.textContent?.trim() === 'Activate' || item.textContent?.trim() === 'Deactivate'
    );
    expect(activateButton).toBeUndefined();
  });

  it('marks the selected row while the user workspace overlay is open', async () => {
    mockUseUsersPageData.mockReturnValue(buildHookData());
    await renderPage('/workspace/administration/users?selected=user-1&tab=details');

    const row = document.querySelector('[data-testid="row-user-1"]');
    expect(row).not.toBeNull();
    expect(row.getAttribute('data-row-class')).toContain('ring-brand-200');
    expect(document.body.textContent).toContain('Alice Admin');
  });

  it('keeps diagnostics collapsed by default and expands on demand', async () => {
    mockUseUsersPageData.mockReturnValue(buildHookData());
    await renderPage('/workspace/administration/users');

    expect(document.body.textContent).not.toContain('Pagination & API Latency');

    const toggleDiagnostics = Array.from(document.querySelectorAll('button')).find((item) =>
      item.textContent?.includes('Workspace Diagnostics')
    );
    expect(toggleDiagnostics).not.toBeNull();

    await act(async () => {
      toggleDiagnostics.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(document.body.textContent).toContain('Pagination & API Latency');
  });
});
