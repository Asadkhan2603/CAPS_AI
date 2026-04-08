// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import GrievancesPage from './GrievancesPage';

const {
  mockPushToast,
  mockUseAuth,
  mockListMyGrievances,
  mockListGrievanceInbox,
  mockGetGrievance,
  mockListGrievanceForwardTargets
} = vi.hoisted(() => ({
  mockPushToast: vi.fn(),
  mockUseAuth: vi.fn(),
  mockListMyGrievances: vi.fn(),
  mockListGrievanceInbox: vi.fn(),
  mockGetGrievance: vi.fn(),
  mockListGrievanceForwardTargets: vi.fn()
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: mockPushToast
  })
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('../services/grievancesApi', () => ({
  addGrievanceComment: vi.fn(),
  addGrievanceInternalNote: vi.fn(),
  createGrievance: vi.fn(),
  forwardGrievance: vi.fn(),
  getGrievance: mockGetGrievance,
  listGrievanceForwardTargets: mockListGrievanceForwardTargets,
  listGrievanceInbox: mockListGrievanceInbox,
  listMyGrievances: mockListMyGrievances,
  reopenGrievance: vi.fn(),
  updateGrievanceStatus: vi.fn()
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

vi.mock('../components/ui/FileUpload', () => ({
  default: () => <div data-testid="file-upload" />
}));

vi.mock('../components/ui/Table', () => ({
  default: () => <div data-testid="grievance-table" />
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage(mode = 'student') {
  mockUseAuth.mockReturnValue({
    user: {
      id: `${mode}-1`,
      role: mode === 'student' ? 'student' : 'teacher'
    }
  });

  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={['/workspace/profile/grievances']}>
        <GrievancesPage mode={mode} />
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

describe('GrievancesPage student banner action', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockPushToast.mockReset();
    mockUseAuth.mockReset();
    mockListMyGrievances.mockReset();
    mockListGrievanceInbox.mockReset();
    mockGetGrievance.mockReset();
    mockListGrievanceForwardTargets.mockReset();
    mockListMyGrievances.mockResolvedValue([]);
    mockListGrievanceInbox.mockResolvedValue([]);
    mockGetGrievance.mockResolvedValue(null);
    mockListGrievanceForwardTargets.mockResolvedValue([]);
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

  it('shows a placeholder toast when the student banner create button is clicked', async () => {
    await renderPage('student');

    await clickButton('CREATE');

    expect(mockPushToast).toHaveBeenCalledWith({
      title: 'CREATE',
      description: 'Create button is clickable. The grievance banner shortcut will be connected next.',
      variant: 'info'
    });
  });

  it('does not render the banner create button for staff grievance modes', async () => {
    await renderPage('coordinator');

    expect(document.querySelector('button[aria-label="CREATE"]')).toBeNull();
  });
});
