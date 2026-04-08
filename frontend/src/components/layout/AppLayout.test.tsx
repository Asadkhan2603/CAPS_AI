// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom';
import AppLayout from './AppLayout';

const { mockApiGet } = vi.hoisted(() => ({
  mockApiGet: vi.fn()
}));

vi.mock('../../hooks/useAuthorizedImage', () => ({
  useAuthorizedImage: () => null
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: vi.fn()
  })
}));

vi.mock('../ui/Toast', () => ({
  default: () => null
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    defaults: {
      baseURL: 'http://localhost/api/v1'
    },
    get: mockApiGet,
    post: vi.fn()
  }
}));

vi.mock('../../config/navigationGroups', () => ({
  getVisibleNavigationGroups: () => [
    {
      key: 'home',
      label: 'Home',
      items: [{ label: 'Dashboard', to: '/dashboard' }]
    },
    {
      key: 'academics',
      label: 'Students & Academics',
      items: [{ label: 'Students', to: '/students' }]
    },
    {
      key: 'communication',
      label: 'Communication',
      items: [{ label: 'Announcements', to: '/announcements' }]
    }
  ],
  getWorkspaceItemPath: (_groupKey: string, to: string) => to
}));

type MediaState = {
  desktop: boolean;
  tablet: boolean;
};

const testUser = {
  id: 'user-1',
  full_name: 'Asad Super Admin',
  email: 'asad@example.com',
  role: 'admin',
  admin_type: 'super_admin'
};

let mediaState: MediaState = { desktop: false, tablet: false };
let container: HTMLDivElement | null = null;
let root: Root | null = null;
const reactActEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT?: boolean;
};

function setMediaState(nextState: MediaState) {
  mediaState = nextState;
}

function installMatchMedia() {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => {
      const matches = query === '(min-width: 1024px)'
        ? mediaState.desktop
        : query === '(min-width: 768px) and (max-width: 1023px)'
          ? mediaState.tablet
          : false;

      return {
        matches,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn()
      };
    }
  });
}

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function LayoutHarness() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <>
      <button type="button" aria-label="External navigate" onClick={() => navigate('/students')}>
        External navigate
      </button>
      <AppLayout
        user={testUser}
        sessionBootstrap={{ unread_notification_count: 3, branding: { updated_at: '2026-04-07T00:00:00Z' } }}
        isDark={false}
        onToggleTheme={() => {}}
        onLogout={() => {}}
        toasts={[]}
        onDismissToast={() => {}}
        locationKey={location.key}
      >
        <div data-testid="route-indicator">{location.pathname}</div>
      </AppLayout>
    </>
  );
}

async function renderLayout(initialEntry = '/dashboard') {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root?.render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <LayoutHarness />
      </MemoryRouter>
    );
    await waitForTick();
  });
}

async function clickElement(element: Element | null) {
  expect(element).not.toBeNull();
  await act(async () => {
    (element as HTMLElement).focus();
    (element as HTMLElement).dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await waitForTick();
  });
}

async function pressEscape() {
  await act(async () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await waitForTick();
    await waitForTick();
  });
}

describe('AppLayout navigation interactions', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mediaState = { desktop: false, tablet: false };
    installMatchMedia();
    mockApiGet.mockResolvedValue({ data: { count: 0 } });
    Object.defineProperty(window, 'scrollY', {
      configurable: true,
      writable: true,
      value: 148
    });
    window.scrollTo = vi.fn();
    window.localStorage.clear();
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
    document.body.style.cssText = '';
    document.documentElement.style.cssText = '';
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = false;
    vi.clearAllMocks();
  });

  it('locks body scroll for the mobile drawer and closes it on route changes', async () => {
    setMediaState({ desktop: false, tablet: false });
    await renderLayout();

    const menuButton = document.querySelector('button[aria-label="Open navigation"]');
    await clickElement(menuButton);

    expect(document.querySelector('[aria-label="Navigation drawer"]')).not.toBeNull();
    expect(document.body.style.position).toBe('fixed');
    expect(document.documentElement.style.overflow).toBe('hidden');

    const navigateButton = document.querySelector('button[aria-label="External navigate"]');
    await clickElement(navigateButton);

    expect(document.querySelector('[aria-label="Navigation drawer"]')).toBeNull();
    expect(document.body.style.position).toBe('');
    expect(document.documentElement.style.overflow).toBe('');
    expect(window.scrollTo).toHaveBeenCalledWith(0, 148);
  });

  it('opens the tablet navigation panel and closes it on Escape', async () => {
    setMediaState({ desktop: false, tablet: true });
    await renderLayout();

    const menuButton = document.querySelector('button[aria-label="Open navigation"]') as HTMLButtonElement | null;
    await clickElement(menuButton);

    expect(document.querySelector('[aria-label="Navigation panel"]')).not.toBeNull();

    await pressEscape();

    expect(document.querySelector('[aria-label="Navigation panel"]')).toBeNull();
  });

  it('closes top-bar overlays with Escape', async () => {
    setMediaState({ desktop: false, tablet: false });
    await renderLayout();

    const moreActionsButton = document.querySelector('button[aria-label="More actions"]') as HTMLButtonElement | null;
    await clickElement(moreActionsButton);
    expect(document.querySelector('[aria-label="More actions"][role="menu"]')).not.toBeNull();

    await pressEscape();

    expect(document.querySelector('[aria-label="More actions"][role="menu"]')).toBeNull();

    const searchButton = document.querySelector('button[aria-label="Search"]') as HTMLButtonElement | null;
    await clickElement(searchButton);
    expect(document.querySelector('[aria-label="Quick search"]')).not.toBeNull();

    await pressEscape();

    expect(document.querySelector('[aria-label="Quick search"]')).toBeNull();
  });
});
