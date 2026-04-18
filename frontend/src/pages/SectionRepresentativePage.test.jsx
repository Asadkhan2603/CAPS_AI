// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SectionRepresentativePage from './SectionRepresentativePage';

const { mockDashboard, mockPushToast, mockUseAuth } = vi.hoisted(() => ({
  mockDashboard: vi.fn(),
  mockPushToast: vi.fn(),
  mockUseAuth: vi.fn()
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({ pushToast: mockPushToast })
}));

vi.mock('../services/sectionsApi', () => ({
  getSectionRepresentativeDashboard: (...args) => mockDashboard(...args)
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root.render(<SectionRepresentativePage />);
    await waitForTick();
    await waitForTick();
  });
}

describe('SectionRepresentativePage', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockDashboard.mockReset();
    mockPushToast.mockReset();
    mockUseAuth.mockReturnValue({
      user: {
        role: 'student',
        extended_roles: ['class_representative'],
        role_scope: { class_representative: { class_id: 'section-1', seat: 'cr_1' } }
      }
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

  it('renders assigned CR dashboard data, contact links, and empty states', async () => {
    mockDashboard.mockResolvedValue({
      section_id: 'section-1',
      section_name: 'CSE 4A',
      seat: 'cr_1',
      generated_at: '2026-04-16T08:00:00Z',
      attendance_summary: { total_students: 42, shortage_risk_count: 1 },
      attendance_risk_students: [
        {
          student_id: 'student-1',
          student_name: 'Low Attendance Student',
          roll_number: 'R001',
          attendance_percent: 62,
          total_marked_slots: 10,
          absent_slots: 4
        }
      ],
      assignments: [
        {
          assignment_id: 'assignment-1',
          title: 'Lab Report',
          due_date: '2026-04-20T00:00:00Z',
          status: 'open',
          total_students: 42,
          missing_submission_count: 1,
          missing_students: [{ student_id: 'student-2', student_name: 'Missing Student', roll_number: 'R002' }]
        }
      ],
      authority_contacts: [
        {
          label: 'HOD',
          full_name: 'HOD Contact',
          email: 'hod@example.com',
          phone: '1112223333',
          role: 'hod',
          has_email: true,
          has_phone: true
        },
        {
          label: 'Dean',
          full_name: 'Dean Contact',
          email: null,
          phone: null,
          role: 'dean',
          has_email: false,
          has_phone: false
        }
      ]
    });

    await renderPage();

    expect(mockDashboard).toHaveBeenCalledWith('section-1');
    expect(document.body.textContent).toContain('CR Workspace');
    expect(document.body.textContent).toContain('Section: CSE 4A');
    expect(document.body.textContent).toContain('Seat: CR-1');
    expect(document.body.textContent).toContain('Low Attendance Student');
    expect(document.body.textContent).toContain('Lab Report');
    expect(document.body.textContent).toContain('Missing Student');
    expect(document.body.textContent).toContain('HOD Contact');
    expect(document.querySelector('a[href="mailto:hod@example.com"]')).not.toBeNull();
    expect(document.querySelector('a[href="tel:1112223333"]')).not.toBeNull();
    expect(document.body.textContent).toContain('No email available');
    expect(document.body.textContent).toContain('No phone available');
  });

  it('shows a useful message when no CR section is assigned', async () => {
    mockUseAuth.mockReturnValue({ user: { role: 'student', extended_roles: ['class_representative'], role_scope: {} } });

    await renderPage();

    expect(mockDashboard).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain('Your account is not assigned to a CR section yet.');
  });

  it('shows error feedback when dashboard load fails', async () => {
    mockDashboard.mockRejectedValue({ response: { data: { detail: 'Not allowed to view this representative dashboard' } } });

    await renderPage();

    expect(document.body.textContent).toContain('Not allowed to view this representative dashboard');
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Load failed', variant: 'error' })
    );
  });
});
