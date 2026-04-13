// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import GrievancesPage from './GrievancesPage';

const {
  mockPushToast,
  mockUseAuth,
  mockCreateGrievance,
  mockUpdateGrievanceStatus,
  mockListMyGrievances,
  mockListGrievanceInbox,
  mockGetGrievance,
  mockListGrievanceForwardTargets
} = vi.hoisted(() => ({
  mockPushToast: vi.fn(),
  mockUseAuth: vi.fn(),
  mockCreateGrievance: vi.fn(),
  mockUpdateGrievanceStatus: vi.fn(),
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
  createGrievance: mockCreateGrievance,
  forwardGrievance: vi.fn(),
  getGrievance: mockGetGrievance,
  listGrievanceForwardTargets: mockListGrievanceForwardTargets,
  listGrievanceInbox: mockListGrievanceInbox,
  listMyGrievances: mockListMyGrievances,
  reopenGrievance: vi.fn(),
  updateGrievanceStatus: mockUpdateGrievanceStatus
}));

vi.mock('../components/ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>
}));

vi.mock('../components/ui/Badge', () => ({
  default: ({ children }) => <span>{children}</span>
}));

vi.mock('../components/ui/FormInput', () => ({
  default: React.forwardRef(({ label, as = 'input', children, ...props }, ref) => {
    const Component = as;
    return (
      <label>
        {label ? <span>{label}</span> : null}
        <Component ref={ref} {...props}>{children}</Component>
      </label>
    );
  })
}));

vi.mock('../components/ui/FileUpload', () => ({
  default: () => <div data-testid="file-upload" />
}));

vi.mock('../components/ui/Modal', () => ({
  default: ({ open, title, children, onClose }) => (
    open ? (
      <div data-testid="grievance-create-modal">
        <h3>{title}</h3>
        <button type="button" aria-label="Close modal" onClick={onClose}>Close</button>
        {children}
      </div>
    ) : null
  )
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

function setInputValue(element, value) {
  const prototype = element instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  const valueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
  valueSetter.call(element, value);
  element.dispatchEvent(new Event('input', { bubbles: true }));
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
    mockCreateGrievance.mockReset();
    mockUpdateGrievanceStatus.mockReset();
    mockListMyGrievances.mockReset();
    mockListGrievanceInbox.mockReset();
    mockGetGrievance.mockReset();
    mockListGrievanceForwardTargets.mockReset();
    mockListMyGrievances.mockResolvedValue([]);
    mockListGrievanceInbox.mockResolvedValue([]);
    mockGetGrievance.mockResolvedValue(null);
    mockListGrievanceForwardTargets.mockResolvedValue([]);
    mockCreateGrievance.mockResolvedValue({
      id: 'grievance-1',
      public_id: 'GRV-0001',
      title: 'Test grievance',
      current_stage: 'coordinator'
    });
    mockUpdateGrievanceStatus.mockResolvedValue({
      id: 'grievance-1',
      public_id: 'GRV-0001',
      title: 'Test grievance',
      current_stage: 'coordinator',
      status: 'resolved'
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

  it('opens the grievance create modal when the student banner create button is clicked', async () => {
    await renderPage('student');

    await clickButton('CREATE');

    expect(document.querySelector('[data-testid="grievance-create-modal"]')).not.toBeNull();
    expect(document.body.textContent).toContain('Submit New Grievance');
    expect(mockPushToast).not.toHaveBeenCalled();
  });

  it('shows a durable confirmation card after a successful student grievance submission', async () => {
    await renderPage('student');

    await clickButton('CREATE');

    const titleInput = document.querySelector('input[required]');
    const descriptionInput = document.querySelector('textarea[required]');
    const submitButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent === 'Submit Grievance');

    expect(titleInput).not.toBeNull();
    expect(descriptionInput).not.toBeNull();
    expect(submitButton).not.toBeNull();

    await act(async () => {
      setInputValue(titleInput, 'Lab issue');
      setInputValue(descriptionInput, 'The lab system is not working.');
      await waitForTick();
    });

    await act(async () => {
      submitButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockCreateGrievance).toHaveBeenCalledWith({
      category: 'academic',
      title: 'Lab issue',
      description: 'The lab system is not working.',
      attachment: null
    });
    expect(document.body.textContent).toContain('Grievance Submitted');
    expect(document.body.textContent).toContain('GRV-0001');
    expect(document.querySelector('[data-testid="grievance-create-modal"]')).toBeNull();
  });

  it('requests the next page when load more is clicked', async () => {
    mockListMyGrievances
      .mockResolvedValueOnce(Array.from({ length: 20 }, (_, index) => ({ id: `grievance-${index + 1}` })))
      .mockResolvedValueOnce([{ id: 'grievance-21' }]);

    await renderPage('student');

    expect(mockListMyGrievances).toHaveBeenNthCalledWith(1, { skip: 0, limit: 20 });

    const loadMoreButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent === 'Load More');
    expect(loadMoreButton).not.toBeNull();

    await act(async () => {
      loadMoreButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockListMyGrievances).toHaveBeenNthCalledWith(2, { skip: 20, limit: 20 });
  });

  it('does not render the banner create button for staff grievance modes', async () => {
    await renderPage('coordinator');

    expect(document.querySelector('button[aria-label="CREATE"]')).toBeNull();
  });

  it('opens a resolve modal for staff and submits the resolution note', async () => {
    mockListGrievanceInbox.mockResolvedValue([{ id: 'grievance-1', status: 'open', current_stage: 'coordinator' }]);
    mockGetGrievance.mockResolvedValue({
      id: 'grievance-1',
      public_id: 'GRV-0001',
      title: 'Lab issue',
      description: 'Projector not working',
      current_stage: 'coordinator',
      status: 'open',
      is_overdue: false,
      timeline: []
    });

    await renderPage('coordinator');

    const resolveButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent === 'Resolve');
    expect(resolveButton).not.toBeNull();

    await act(async () => {
      resolveButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(document.body.textContent).toContain('Resolve Grievance');
    const resolutionTextarea = Array.from(document.querySelectorAll('textarea')).at(-1);
    const confirmButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent === 'Confirm Resolution');

    expect(resolutionTextarea).not.toBeNull();
    expect(confirmButton).not.toBeNull();

    await act(async () => {
      setInputValue(resolutionTextarea, 'Issue has been verified and resolved.');
      await waitForTick();
    });

    await act(async () => {
      confirmButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockUpdateGrievanceStatus).toHaveBeenCalledWith('grievance-1', 'resolved', 'Issue has been verified and resolved.');
    expect(document.body.textContent).not.toContain('Resolve Grievance');
  });
});
