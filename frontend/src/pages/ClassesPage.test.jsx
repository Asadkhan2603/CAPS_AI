// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ClassesPage from './ClassesPage';

const {
  mockAssignRepresentative,
  mockGetRepresentatives,
  mockGetSections,
  mockPushToast,
  mockRemoveRepresentative,
  mockUseAuth
} = vi.hoisted(() => ({
  mockAssignRepresentative: vi.fn(),
  mockGetRepresentatives: vi.fn(),
  mockGetSections: vi.fn(),
  mockPushToast: vi.fn(),
  mockRemoveRepresentative: vi.fn(),
  mockUseAuth: vi.fn()
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({ pushToast: mockPushToast })
}));

vi.mock('../services/apiClient', () => ({
  apiClient: { get: vi.fn().mockResolvedValue({ data: {} }) }
}));

vi.mock('../services/paginatedLookups', () => ({
  searchLookupOptions: vi.fn().mockResolvedValue([])
}));

vi.mock('../components/ui/SearchableSelect', () => ({
  default: ({ label, value = '', onValueChange, disabled }) => (
    <label>
      {label}
      <select aria-label={label} value={value} disabled={disabled} onChange={(event) => onValueChange?.(event.target.value)}>
        <option value="">None</option>
      </select>
    </label>
  )
}));

vi.mock('../components/ui/Table', () => ({
  default: ({ columns = [], data = [] }) => (
    <div data-testid="sections-table">
      {data.map((row) => (
        <div key={row.id}>
          {columns.map((column) => (
            <div key={column.key}>{column.render ? column.render(row) : row[column.key] ?? '-'}</div>
          ))}
        </div>
      ))}
    </div>
  )
}));

vi.mock('../services/sectionsApi', () => ({
  assignSectionRepresentative: (...args) => mockAssignRepresentative(...args),
  createSection: vi.fn().mockResolvedValue({}),
  getSectionRepresentatives: (...args) => mockGetRepresentatives(...args),
  getSections: (...args) => mockGetSections(...args),
  removeSectionRepresentative: (...args) => mockRemoveRepresentative(...args)
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function setInputValue(element, value) {
  const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  valueSetter.call(element, value);
  element.dispatchEvent(new Event('input', { bubbles: true }));
}

async function renderPage() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root.render(<ClassesPage />);
    await waitForTick();
    await waitForTick();
  });
}

describe('ClassesPage class representative panel', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockAssignRepresentative.mockReset();
    mockGetRepresentatives.mockReset();
    mockGetSections.mockReset();
    mockPushToast.mockReset();
    mockRemoveRepresentative.mockReset();
    mockUseAuth.mockReturnValue({ user: { role: 'admin', admin_type: 'super_admin' } });
    mockGetSections.mockResolvedValue({
      data: [
        {
          id: 'section-1',
          name: 'CSE 4A',
          class_representatives: { cr_1: { user_id: 'student-1', full_name: 'Current CR' }, cr_2: {} }
        }
      ]
    });
    mockGetRepresentatives.mockResolvedValue({
      section_id: 'section-1',
      section_name: 'CSE 4A',
      representatives: { cr_1: { user_id: 'student-1', full_name: 'Current CR' }, cr_2: { user_id: null, full_name: null } },
      candidate_students: [
        { student_user_id: 'student-1', full_name: 'Current CR' },
        { student_user_id: 'student-2', full_name: 'Replacement CR' }
      ]
    });
    mockAssignRepresentative.mockResolvedValue({
      section_id: 'section-1',
      section_name: 'CSE 4A',
      representatives: { cr_1: { user_id: 'student-2', full_name: 'Replacement CR' }, cr_2: { user_id: null, full_name: null } },
      candidate_students: []
    });
    mockRemoveRepresentative.mockResolvedValue({
      section_id: 'section-1',
      section_name: 'CSE 4A',
      representatives: { cr_1: { user_id: null, full_name: null }, cr_2: { user_id: null, full_name: null } },
      candidate_students: []
    });
  });

  afterEach(async () => {
    await act(async () => {
      root?.unmount();
      await waitForTick();
    });
    root = null;
    container?.remove();
    container = null;
    document.body.innerHTML = '';
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = false;
  });

  it('loads CR seats and requires valid assign/remove details', async () => {
    await renderPage();

    const manageButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Manage CRs'));
    expect(manageButton).not.toBeNull();
    await act(async () => {
      manageButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockGetRepresentatives).toHaveBeenCalledWith('section-1');
    expect(document.body.textContent).toContain('Class Representative Seats');
    expect(document.body.textContent).toContain('Current CR');

    const assignButtons = Array.from(document.querySelectorAll('button')).filter((button) => button.textContent.includes('Assign Seat'));
    expect(assignButtons[1].disabled).toBe(true);

    const clearButtons = Array.from(document.querySelectorAll('button')).filter((button) => button.textContent.includes('Clear Seat'));
    expect(clearButtons[0].disabled).toBe(true);
  });

  it('requires confirmation before replacing an assigned CR seat', async () => {
    await renderPage();
    const manageButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Manage CRs'));
    await act(async () => {
      manageButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    const studentSelect = Array.from(document.querySelectorAll('select')).find((select) =>
      Array.from(select.options).some((option) => option.value === 'student-2')
    );
    expect(studentSelect).not.toBeNull();
    await act(async () => {
      studentSelect.value = 'student-2';
      studentSelect.dispatchEvent(new Event('change', { bubbles: true }));
      await waitForTick();
    });

    const reasonInput = Array.from(document.querySelectorAll('input')).find((input) => input.placeholder.includes('CR-1'));
    expect(reasonInput).not.toBeNull();
    await act(async () => {
      setInputValue(reasonInput, 'Approved replacement');
      await waitForTick();
    });

    const reviewButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Review Replace'));
    expect(reviewButton).not.toBeNull();
    await act(async () => {
      reviewButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });
    expect(mockAssignRepresentative).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain('This will replace Current CR for CR-1');

    const confirmButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent.includes('Confirm Replace'));
    expect(confirmButton).not.toBeNull();
    await act(async () => {
      confirmButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockAssignRepresentative).toHaveBeenCalledWith('section-1', 'cr_1', {
      student_user_id: 'student-2',
      reason: 'Approved replacement'
    });
  });
});
