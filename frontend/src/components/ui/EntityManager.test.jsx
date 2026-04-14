// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EntityManager from './EntityManager';

const { mockApiGet, mockPushToast } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockPushToast: vi.fn(),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children }) => <div>{children}</div>,
  },
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({ pushToast: mockPushToast }),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    get: (...args) => mockApiGet(...args),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('./Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>,
}));

vi.mock('./Table', () => ({
  default: ({ data }) => <div data-testid="table">Rows: {data.length}</div>,
}));

vi.mock('./entityManager/DeleteReviewPrompt', () => ({
  default: () => null,
}));

vi.mock('./entityManager/EntityFormOverlay', () => ({
  default: () => null,
}));

vi.mock('./entityManager/EntitySearchOverlay', () => ({
  default: () => null,
}));

vi.mock('./entityManager/useDeleteGovernance', () => ({
  useDeleteGovernance: () => ({
    closeDeleteReviewPrompt: vi.fn(),
    deleteError: '',
    deleteReviewId: '',
    deleteReviewMetadata: {},
    deleteReviewPromptConfig: {},
    deleteReviewPromptOpen: false,
    deleteReviewTarget: null,
    onDelete: vi.fn(),
    setDeleteReviewId: vi.fn(),
    setDeleteReviewMetadata: vi.fn(),
  }),
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function renderComponent() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(
      <EntityManager
        title="Users"
        endpoint="/users/"
        columns={[{ key: 'name', label: 'Name' }]}
        filters={[{ name: 'status', label: 'Status' }]}
      />
    );
    await waitForTick();
  });
}

describe('EntityManager', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockApiGet.mockReset();
    mockPushToast.mockReset();
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

  it('shows a shared loading placeholder before list data resolves', async () => {
    const pending = deferred();
    mockApiGet.mockReturnValueOnce(pending.promise);

    await renderComponent();

    expect(document.body.textContent).toContain('Loading users...');

    await act(async () => {
      pending.resolve({ data: [] });
      await waitForTick();
      await waitForTick();
    });
  });

  it('shows a shared empty state when the list resolves with no rows', async () => {
    mockApiGet.mockResolvedValueOnce({ data: [] });

    await renderComponent();

    expect(document.body.textContent).toContain('No users found');
    expect(document.body.textContent).toContain('Reset Filters');
  });

  it('shows a retryable load error and can recover on retry', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('network down'));

    await renderComponent();

    expect(document.body.textContent).toContain('Load failed');
    expect(document.body.textContent).toContain('Retry');
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Load failed',
        variant: 'error',
      })
    );

    mockApiGet.mockResolvedValueOnce({ data: [] });
    const retryButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('Retry'));
    expect(retryButton).toBeTruthy();

    await act(async () => {
      retryButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(document.body.textContent).toContain('No users found');
  });
});
