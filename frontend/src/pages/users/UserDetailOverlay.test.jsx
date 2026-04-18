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

function setInputValue(element, value) {
  const prototype = element instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  const valueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
  valueSetter.call(element, value);
  element.dispatchEvent(new Event('input', { bubbles: true }));
}

function buildProps(overrides = {}) {
  const selectedUser = {
    id: 'user-1',
    full_name: 'Teacher One',
    email: 'teacher.one@example.com',
    role: 'teacher',
    admin_type: null,
    is_active: true,
    extended_roles: ['class_coordinator'],
    role_scope: { class_coordinator: { class_id: 'section-1' } },
    profile: {
      phone: '',
      department: 'Engineering',
      designation: 'Lecturer',
      organization: 'CAPS'
    },
    created_at: '2026-04-10T09:00:00Z',
    updated_at: '2026-04-12T09:00:00Z',
    last_active_at: '2026-04-14T09:00:00Z'
  };
  return {
    batches: [],
    clubs: [{ id: 'club-1', name: 'Robotics Club' }],
    close: vi.fn(),
    departments: [],
    faculties: [],
    getEffectiveExtensions: () => ['class_coordinator'],
    getEffectiveScope: () => ({ class_coordinator: { class_id: 'section-1' } }),
    programs: [],
    savePermissions: vi.fn().mockResolvedValue(undefined),
    savingIds: [],
    sections: [{ id: 'section-1', name: 'Section A' }],
    selectedTab: 'details',
    selectedUser,
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
    createPermissionTemplate: vi.fn().mockResolvedValue({ id: 'template-1', name: 'Coordinator Starter' }),
    updatePermissionTemplate: vi.fn().mockResolvedValue({ id: 'template-1', name: 'Coordinator Starter' }),
    deletePermissionTemplate: vi.fn().mockResolvedValue(undefined),
    permissionTemplateSaving: false,
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

describe('UserDetailOverlay details and permissions', () => {
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

  it('shows diff preview before saving edited user details', async () => {
    const props = buildProps({ selectedTab: 'details' });
    await renderOverlay(props);

    const editButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Edit Safe Fields'));
    expect(editButton).not.toBeNull();

    await act(async () => {
      editButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    const fullNameInput = Array.from(document.querySelectorAll('input')).find(
      (input) => input.value === 'Teacher One'
    );
    expect(fullNameInput).not.toBeNull();
    await act(async () => {
      setInputValue(fullNameInput, 'Teacher One Updated');
      await waitForTick();
    });

    const previewButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Preview Changes'));
    expect(previewButton).not.toBeNull();
    await act(async () => {
      previewButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(document.body.textContent).toContain('Diff Preview');
    expect(document.body.textContent).toContain('Before: Teacher One');
    expect(document.body.textContent).toContain('After: Teacher One Updated');
  });

  it('renders a centered below-header overlay with readable details sections by default', async () => {
    const props = buildProps({ selectedTab: 'details', topOffsetPx: 92 });
    await renderOverlay(props);

    const overlayShell = document.querySelector('[data-testid="users-detail-overlay-shell"]');
    const dialog = document.querySelector('[data-testid="users-detail-overlay"]');
    expect(overlayShell).not.toBeNull();
    expect(overlayShell.style.top).toBe('92px');
    expect(dialog).not.toBeNull();
    expect(dialog.className).toContain('sm:w-[92vw]');
    expect(dialog.className).not.toContain('right-0');

    expect(document.body.textContent).toContain('Contact');
    expect(document.body.textContent).toContain('Organization');
    expect(document.body.textContent).toContain('Governance Context');
    expect(document.body.textContent).toContain('Copy email');

    const matchingInput = Array.from(document.querySelectorAll('input')).find((input) => input.value === 'Teacher One');
    expect(matchingInput).toBeUndefined();
  });

  it('renders effective access chips for permission scope preview', async () => {
    const props = buildProps({ selectedTab: 'permissions' });
    await renderOverlay(props);

    expect(document.body.textContent).toContain('Effective Access Preview');
    expect(document.body.textContent).toContain('Base: Teacher');
    expect(document.body.textContent).toContain('Extension: Class Coordinator');
    expect(document.body.textContent).toContain('Section: Section A');
  });

  it('creates a permission template from current draft permissions', async () => {
    const createPermissionTemplate = vi.fn().mockResolvedValue({ id: 'template-9', name: 'Class Lead Template' });
    const props = buildProps({
      selectedTab: 'permissions',
      createPermissionTemplate
    });
    await renderOverlay(props);

    const nameInput = Array.from(document.querySelectorAll('input')).find(
      (input) => input.placeholder === 'Template name'
    );
    expect(nameInput).not.toBeNull();
    await act(async () => {
      setInputValue(nameInput, 'Class Lead Template');
      await waitForTick();
    });

    const createButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent.includes('Save As New Template')
    );
    expect(createButton).not.toBeNull();
    await act(async () => {
      createButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(createPermissionTemplate).toHaveBeenCalledWith({
      name: 'Class Lead Template',
      description: null,
      role: 'teacher',
      admin_type: null,
      extended_roles: ['class_coordinator'],
      role_scope: { class_coordinator: { class_id: 'section-1' } }
    });
  });

  it('requires reason before allowing risk deactivation', async () => {
    const onStatusChange = vi.fn().mockResolvedValue(undefined);
    const props = buildProps({ selectedTab: 'risk', onStatusChange });
    await renderOverlay(props);

    const deactivateButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Deactivate User'));
    expect(deactivateButton).not.toBeNull();
    expect(deactivateButton.disabled).toBe(true);

    const reasonInput = Array.from(document.querySelectorAll('input')).find((input) => input.placeholder === 'Required reason for status change');
    expect(reasonInput).not.toBeNull();
    await act(async () => {
      setInputValue(reasonInput, 'Compliance issue');
      await waitForTick();
    });

    expect(deactivateButton.disabled).toBe(false);
    await act(async () => {
      deactivateButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(onStatusChange).toHaveBeenCalledWith(false, 'Compliance issue');
  });
});
