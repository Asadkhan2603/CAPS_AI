// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AnnouncementsPage from './AnnouncementsPage';

const { mockUseAuth, mockApiGet } = vi.hoisted(() => ({
  mockUseAuth: vi.fn(),
  mockApiGet: vi.fn()
}));

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: vi.fn()
  })
}));

vi.mock('../../utils/errorToast', () => ({
  pushApiErrorToast: vi.fn()
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    get: mockApiGet,
    post: vi.fn()
  }
}));

vi.mock('../../components/communication/CommunicationTabs', () => ({
  default: () => <div data-testid="communication-tabs" />
}));

vi.mock('../../components/communication/CommunicationDeliveryModal', () => ({
  default: () => null
}));

vi.mock('../../components/ui/EmptyState', () => ({
  default: ({ title }) => <div>{title}</div>
}));

vi.mock('../../components/communication/AnnouncementCard', () => ({
  default: ({ canInspectDelivery }) => <div data-testid="announcement-card">{String(Boolean(canInspectDelivery))}</div>
}));

vi.mock('../../components/communication/CreateAnnouncementModal', () => ({
  default: ({ canPreviewAudience }) => <div data-testid="create-announcement-modal">{String(Boolean(canPreviewAudience))}</div>
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function buildUser(overrides = {}) {
  return {
    id: 'teacher-1',
    full_name: 'Teacher User',
    email: 'teacher@caps.ai',
    role: 'teacher',
    extended_roles: [],
    ...overrides
  };
}

function mockGetImplementation() {
  mockApiGet.mockImplementation((url) => {
    if (url === '/notices/') {
      return Promise.resolve({
        data: [
          {
            id: 'notice-1',
            title: 'Teacher Notice',
            message: 'Visible test notice',
            scope: 'subject',
            scope_ref_id: 'subject-1',
            created_at: '2026-04-12T10:00:00.000Z',
            priority: 'normal',
            is_read: false
          }
        ]
      });
    }
    if (url === '/batches/' || url === '/sections/' || url === '/subjects/') {
      return Promise.resolve({ data: [] });
    }
    return Promise.resolve({ data: [] });
  });
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage(userOverrides = {}) {
  mockUseAuth.mockReturnValue({
    user: buildUser(userOverrides)
  });

  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={['/workspace/communication/announcements']}>
        <AnnouncementsPage />
      </MemoryRouter>
    );
    await waitForTick();
    await waitForTick();
  });
}

describe('AnnouncementsPage teacher operator gating', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockUseAuth.mockReset();
    mockApiGet.mockReset();
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

  it('keeps operator-only delivery and preview features disabled for plain teachers', async () => {
    await renderPage({ extended_roles: [] });

    expect(document.querySelector('[data-testid="announcement-card"]')?.textContent).toBe('false');
    expect(document.querySelector('[data-testid="create-announcement-modal"]')?.textContent).toBe('false');
  });

  it('enables operator-only delivery and preview features for coordinator-style teachers', async () => {
    await renderPage({ extended_roles: ['class_coordinator'] });

    expect(document.querySelector('[data-testid="announcement-card"]')?.textContent).toBe('true');
    expect(document.querySelector('[data-testid="create-announcement-modal"]')?.textContent).toBe('true');
  });
});
