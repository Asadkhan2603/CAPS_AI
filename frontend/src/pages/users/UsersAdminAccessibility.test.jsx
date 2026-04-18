// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import UserDetailOverlay from './UserDetailOverlay';

vi.mock('../../hooks/useAuthorizedImage', () => ({
  useAuthorizedImage: () => null
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function buildA11yProps(overrides = {}) {
  return {
    batches: [],
    clubs: [],
    close: vi.fn(),
    departments: [],
    faculties: [],
    getEffectiveExtensions: () => [],
    getEffectiveScope: () => ({}),
    programs: [],
    savePermissions: vi.fn().mockResolvedValue(undefined),
    savingIds: [],
    sections: [],
    selectedTab: 'risk',
    selectedUser: {
      id: 'user-a11y',
      full_name: 'Accessible Admin',
      email: 'accessible.admin@example.com',
      role: 'admin',
      admin_type: 'super_admin',
      is_active: true,
      extended_roles: [],
      role_scope: {},
      profile: {},
      created_at: '2026-04-10T09:00:00Z',
      updated_at: '2026-04-12T09:00:00Z',
      last_active_at: '2026-04-14T09:00:00Z'
    },
    semesters: [],
    setSelectedTab: vi.fn(),
    specializations: [],
    toggleExtension: vi.fn(),
    updateClassCoordinatorScope: vi.fn(),
    updateClubPresidentScope: vi.fn(),
    updateClassRepresentativeScope: vi.fn(),
    activityItems: [],
    activityLoading: false,
    refreshActivity: vi.fn(),
    onStatusChange: vi.fn().mockResolvedValue(undefined),
    permissionTemplates: [],
    applyPermissionTemplate: vi.fn(),
    resetPermissionDraft: vi.fn(),
    onSaveDetails: vi.fn().mockResolvedValue(undefined),
    detailsSaving: false,
    capabilities: {
      workspace: true,
      activity: true,
      bulk_operations: true,
      permission_templates: true,
      invitations: true,
      import_export: true,
      inline_editing: true,
      compact_density: true,
      responsive_workflows: true
    },
    ...overrides
  };
}

async function renderOverlay(props) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root.render(<UserDetailOverlay {...props} />);
    await waitForTick();
    await waitForTick();
  });
}

describe('Users admin accessibility semantics', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
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

  it('exposes semantic heading, keyboard-focusable controls, and reason field', async () => {
    await renderOverlay(buildA11yProps());

    const heading = document.querySelector('h2');
    expect(heading).not.toBeNull();
    expect(heading.textContent).toContain('Accessible Admin');

    const buttons = Array.from(document.querySelectorAll('button'));
    expect(buttons.length).toBeGreaterThan(0);

    const closeButton = buttons.find((button) => button.querySelector('svg'));
    expect(closeButton).not.toBeNull();
    closeButton.focus();
    expect(document.activeElement).toBe(closeButton);

    const reasonInput = Array.from(document.querySelectorAll('input')).find((input) => input.placeholder === 'Required reason for status change');
    expect(reasonInput).not.toBeNull();
    expect(reasonInput.disabled).toBe(false);
    expect(document.body.textContent).toContain('Reason is required before changing status.');
  });
});
