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

function buildUser(role) {
  return {
    id: `${role}-1`,
    full_name: `${role} user`,
    email: `${role}@caps.ai`,
    role,
    communication_preferences: {}
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
    return Promise.resolve({ data: {} });
  });
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage(role = 'admin') {
  mockUseAuth.mockReturnValue({
    user: buildUser(role),
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

  it('shows placeholder toasts for all visible banner buttons for creators', async () => {
    await renderPage('admin');

    await clickButton('Notification settings');
    await clickButton('FILTER');
    await clickButton('CREATE');

    expect(mockPushToast).toHaveBeenCalledWith({
      title: 'Notification settings',
      description: 'Notification settings button is clickable. The full action will be connected next.',
      variant: 'info'
    });
    expect(mockPushToast).toHaveBeenCalledWith({
      title: 'FILTER',
      description: 'Filter button is clickable. The banner shortcut will be connected next.',
      variant: 'info'
    });
    expect(mockPushToast).toHaveBeenCalledWith({
      title: 'CREATE',
      description: 'Create button is clickable. The quick-create shortcut will be connected next.',
      variant: 'info'
    });
  });

  it('hides the create banner button for non-creator roles', async () => {
    await renderPage('student');

    expect(document.querySelector('button[aria-label="Notification settings"]')).not.toBeNull();
    expect(document.querySelector('button[aria-label="FILTER"]')).not.toBeNull();
    expect(document.querySelector('button[aria-label="CREATE"]')).toBeNull();
  });
});
