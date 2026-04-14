// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminRecoveryPage from './AdminRecoveryPage';

const {
  mockFetchRecoveryItems,
  mockRestoreRecoveryItem,
  mockPushToast,
} = vi.hoisted(() => ({
  mockFetchRecoveryItems: vi.fn(),
  mockRestoreRecoveryItem: vi.fn(),
  mockPushToast: vi.fn(),
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({ pushToast: mockPushToast }),
}));

vi.mock('../../services/adminRecoveryApi', () => ({
  fetchRecoveryItems: (...args) => mockFetchRecoveryItems(...args),
  restoreRecoveryItem: (...args) => mockRestoreRecoveryItem(...args),
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

vi.mock('../../components/ui/Table', () => ({
  default: ({ data = [], rowActions = [] }) => (
    <div data-testid="recovery-table">
      {data.map((row) => (
        <div key={row.id}>
          <span>{row.display_name}</span>
          {rowActions.map((action) => (
            <button key={action.key} type="button" onClick={() => action.onClick(row)}>
              {action.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  ),
}));

vi.mock('../../components/ui/Modal', () => ({
  default: ({ open, title, children }) => (open ? <div><p>{title}</p>{children}</div> : null),
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function buildResponse({
  includeLegacy = false,
  items = null,
} = {}) {
  const catalog = [
    {
      key: 'departments',
      label: 'Departments',
      group: 'Academic structure',
      description: 'Restore deleted academic departments and their structure anchors.',
      legacy: false,
      order: 0,
    },
    {
      key: 'notices',
      label: 'Notices',
      group: 'Communication',
      description: 'Recover published notices removed from the communication stream.',
      legacy: false,
      order: 2,
    },
  ];

  if (includeLegacy) {
    catalog.push({
      key: 'courses',
      label: 'Courses',
      group: 'Legacy',
      description: 'Legacy course records retained for older data models.',
      legacy: true,
      order: 11,
    });
  }

  return {
    timestamp: '2026-04-13T06:00:00.000Z',
    collection: 'notices',
    legacyCollectionsIncluded: includeLegacy,
    catalog,
    summary: { notices: 1, courses: includeLegacy ? 1 : 0 },
    items: items || [
      {
        id: 'notice-1',
        collection: 'notices',
        collectionLabel: 'Notices',
        display_name: 'Midterm Schedule Notice',
        subtitle: 'NTC-2026-APR',
        status_label: 'Inactive',
        deleted_at: '2026-04-13T05:30:00.000Z',
        deleted_by_label: 'Admin One',
        audit_resource_type: 'notices',
      },
    ],
  };
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function clickButtonByText(label) {
  const button = Array.from(document.querySelectorAll('button')).find((item) => item.textContent?.includes(label));
  expect(button).toBeTruthy();
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await waitForTick();
  });
}

async function renderPage() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(<MemoryRouter><AdminRecoveryPage /></MemoryRouter>);
    await waitForTick();
    await waitForTick();
  });
}

describe('AdminRecoveryPage', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockFetchRecoveryItems.mockReset();
    mockRestoreRecoveryItem.mockReset();
    mockPushToast.mockReset();
    mockFetchRecoveryItems.mockImplementation(({ includeLegacy }) => Promise.resolve(buildResponse({ includeLegacy })));
    mockRestoreRecoveryItem.mockResolvedValue({ success: true });
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

  it('renders grouped business labels while keeping legacy collections hidden by default', async () => {
    await renderPage();

    expect(document.body.textContent).toContain('Collection Selector');
    expect(document.body.textContent).toContain('Academic structure');
    expect(document.body.textContent).toContain('Communication');
    expect(document.body.textContent).toContain('Departments');
    expect(document.body.textContent).toContain('Notices');
    expect(document.body.textContent).not.toContain('Courses');
  });

  it('reveals legacy collections only after the toggle is enabled', async () => {
    await renderPage();

    const legacyToggle = document.querySelector('input[type="checkbox"]');
    expect(legacyToggle).toBeTruthy();

    await act(async () => {
      legacyToggle.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockFetchRecoveryItems).toHaveBeenLastCalledWith({ collection: 'notices', includeLegacy: true, limit: 100 });
    expect(document.body.textContent).toContain('Legacy');
    expect(document.body.textContent).toContain('Courses');
  });

  it('opens a confirmation modal before restore and shows a success handoff after restore', async () => {
    await renderPage();

    expect(mockRestoreRecoveryItem).not.toHaveBeenCalled();

    await clickButtonByText('Review Restore');

    expect(document.body.textContent).toContain('Confirm Restore');
    expect(document.body.textContent).toContain('Midterm Schedule Notice');
    expect(mockRestoreRecoveryItem).not.toHaveBeenCalled();

    await clickButtonByText('Confirm Restore');

    expect(mockRestoreRecoveryItem).toHaveBeenCalledWith('notices', 'notice-1');
    expect(document.body.textContent).toContain('Restore completed');
    expect(document.body.textContent).toContain('View restore audit trail');
    const auditLink = Array.from(document.querySelectorAll('a')).find((item) => item.getAttribute('href')?.includes('/audit-logs?action=restore'));
    expect(auditLink).toBeTruthy();
    expect(auditLink.getAttribute('href')).toContain('resource_type=notices');
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Restore completed',
        variant: 'success',
      })
    );
  });

  it('keeps the current list visible when restore fails and shows a scoped error', async () => {
    mockRestoreRecoveryItem.mockRejectedValue(new Error('restore unavailable'));
    await renderPage();

    await clickButtonByText('Review Restore');
    await clickButtonByText('Confirm Restore');

    expect(document.body.textContent).toContain('Restore failed');
    expect(document.body.textContent).toContain('Midterm Schedule Notice');
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Restore failed',
        variant: 'error',
      })
    );
  });

  it('shows a readable empty state for collections with no recoverable rows', async () => {
    mockFetchRecoveryItems.mockResolvedValue(
      buildResponse({
        items: [],
      })
    );

    await renderPage();

    expect(document.body.textContent).toContain('No recoverable items in this category');
    expect(document.body.textContent).toContain('There are no soft-deleted notices waiting for restore review right now.');
  });

  it('shows a readable load error without crashing the page shell and allows retry', async () => {
    mockFetchRecoveryItems
      .mockRejectedValueOnce(new Error('network failure'))
      .mockResolvedValueOnce(buildResponse());

    await renderPage();

    expect(document.body.textContent).toContain('Failed to load recovery items');
    expect(document.body.textContent).toContain('Collection Selector');
    expect(document.body.textContent).toContain('Retry');

    await clickButtonByText('Retry');

    expect(mockFetchRecoveryItems).toHaveBeenCalledTimes(2);
    expect(document.body.textContent).toContain('Midterm Schedule Notice');
  });
});
