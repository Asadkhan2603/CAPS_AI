// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SecurityTab } from './SecurityTab';

const { mockApiGet, mockApiPost, mockApiDelete, mockPushToast } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockApiPost: vi.fn(),
  mockApiDelete: vi.fn(),
  mockPushToast: vi.fn()
}));

vi.mock('framer-motion', () => {
  const motion = new Proxy(
    {},
    {
      get: (_, tag) => ({ children, whileHover, whileTap, transition, initial, animate, exit, ...props }) =>
        React.createElement(tag, props, children)
    }
  );

  return { motion };
});

vi.mock('@simplewebauthn/browser', () => ({
  startRegistration: vi.fn()
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    get: mockApiGet,
    post: mockApiPost,
    delete: mockApiDelete
  }
}));

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: mockPushToast
  })
}));

vi.mock('../ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderTab() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(<SecurityTab />);
    await waitForTick();
    await waitForTick();
  });
}

describe('SecurityTab MFA status rendering', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockApiDelete.mockReset();
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
    delete window.PublicKeyCredential;
  });

  it('renders MFA status using the security settings payload as the source of truth', async () => {
    window.PublicKeyCredential = function PublicKeyCredential() {};
    mockApiGet.mockResolvedValue({
      data: {
        mfa_enabled: true,
        mfa_methods: ['totp', 'sms', 'webauthn'],
        primary_method: 'webauthn',
        method_status: {
          totp: { enabled: true, ready: true },
          sms: {
            enabled: true,
            ready: true,
            phone_number_masked: '+*******4567',
            delivery_configured: true,
            resend_after_seconds: 30,
            expires_in_seconds: 300
          },
          webauthn: {
            enabled: true,
            ready: true,
            credential_count: 1
          }
        },
        webauthn_credentials: [
          {
            credential_id: 'cred-1',
            label: 'Work laptop',
            last_used_at: null
          }
        ],
        password_strength: 'strong',
        sessions_active: 2,
        recovery_codes_remaining: 5
      }
    });

    await renderTab();

    expect(document.body.textContent).toContain('Verified number: +*******4567');
    expect(document.body.textContent).toContain('Codes expire after 5 minutes.');
    expect(document.body.textContent).toContain('You can request another code every 30 seconds.');
    expect(document.body.textContent).toContain('Registered credentials: 1');
    expect(document.body.textContent).toContain('Work laptop');
  });

  it('shows SMS misconfiguration details and WebAuthn unsupported-browser messaging', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        mfa_enabled: false,
        mfa_methods: [],
        primary_method: null,
        method_status: {
          totp: { enabled: false, ready: false },
          sms: {
            enabled: false,
            ready: false,
            phone_number_masked: null,
            delivery_configured: false,
            resend_after_seconds: 30,
            expires_in_seconds: 300
          },
          webauthn: {
            enabled: false,
            ready: false,
            credential_count: 0
          }
        },
        webauthn_credentials: [],
        password_strength: 'strong',
        sessions_active: 1,
        recovery_codes_remaining: 0
      }
    });

    await renderTab();

    expect(document.body.textContent).toContain('SMS delivery is not fully configured.');
    expect(document.body.textContent).toContain('Browser does not support WebAuthn');
  });

  it('opens SMS and WebAuthn setup placeholders from the method buttons', async () => {
    window.PublicKeyCredential = function PublicKeyCredential() {};
    mockApiGet.mockResolvedValue({
      data: {
        mfa_enabled: false,
        mfa_methods: [],
        primary_method: null,
        method_status: {
          totp: { enabled: false, ready: false },
          sms: {
            enabled: false,
            ready: false,
            phone_number_masked: null,
            delivery_configured: true,
            resend_after_seconds: 30,
            expires_in_seconds: 300
          },
          webauthn: {
            enabled: false,
            ready: false,
            credential_count: 0
          }
        },
        webauthn_credentials: [],
        password_strength: 'strong',
        sessions_active: 1,
        recovery_codes_remaining: 0
      }
    });

    await renderTab();

    const smsSetupButton = document.querySelector('button[aria-label="Set up SMS Text Message MFA"]');
    expect(smsSetupButton).not.toBeNull();

    await act(async () => {
      smsSetupButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(document.querySelector('input[placeholder="Example: +15551234567"]')).not.toBeNull();

    const webauthnSetupButton = document.querySelector('button[aria-label="Set up Security Key MFA"]');
    expect(webauthnSetupButton).not.toBeNull();

    await act(async () => {
      webauthnSetupButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
    });

    expect(document.querySelector('input[placeholder="Example: Work laptop"]')).not.toBeNull();
  });
});
