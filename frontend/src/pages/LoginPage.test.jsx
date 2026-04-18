// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LoginPage from './LoginPage';

const {
  mockNavigate,
  mockUseAuth,
  mockPushToast,
  mockApiPost,
  mockPushApiErrorToast
} = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockUseAuth: vi.fn(),
  mockPushToast: vi.fn(),
  mockApiPost: vi.fn(),
  mockPushApiErrorToast: vi.fn()
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate
}));

vi.mock('framer-motion', () => {
  const motion = new Proxy(
    {},
    {
      get: (_, tag) => ({ children, whileHover, whileTap, transition, initial, animate, exit, ...props }) =>
        React.createElement(tag, props, children)
    }
  );

  return {
    AnimatePresence: ({ children }) => children,
    motion,
    useMotionValue: () => ({ set: () => {} }),
    useSpring: (value) => value,
    useTransform: () => 0
  };
});

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    pushToast: mockPushToast
  })
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    post: mockApiPost
  }
}));

vi.mock('../components/ui/Card', () => ({
  default: ({ children, className = '' }) => <section className={className}>{children}</section>
}));

vi.mock('../components/auth/PasswordStrengthMeter', () => ({
  PasswordStrengthMeter: () => null
}));

vi.mock('../utils/errorToast', () => ({
  pushApiErrorToast: mockPushApiErrorToast
}));

vi.mock('../utils/apiError', () => ({
  formatApiError: (_error, fallback) => fallback
}));

vi.mock('@simplewebauthn/browser', () => ({
  startAuthentication: vi.fn()
}));

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderPage(authOverrides = {}) {
  mockUseAuth.mockReturnValue({
    login: vi.fn(),
    completeMfaLogin: vi.fn(),
    beginWebAuthnMfaLogin: vi.fn(),
    completeWebAuthnMfaLogin: vi.fn(),
    isAuthenticated: false,
    checking: false,
    loginAnomaly: null,
    ...authOverrides
  });

  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(<LoginPage />);
    await waitForTick();
  });
}

async function fillAndSubmitPrimaryLogin() {
  const emailInput = document.querySelector('input[name="email"]');
  const passwordInput = document.querySelector('input[name="password"]');
  const form = document.querySelector('form');

  emailInput.value = 'teacher@example.com';
  emailInput.dispatchEvent(new Event('input', { bubbles: true }));
  passwordInput.value = 'password123';
  passwordInput.dispatchEvent(new Event('input', { bubbles: true }));

  await act(async () => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await waitForTick();
    await waitForTick();
  });
}

describe('LoginPage MFA flow', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
    mockNavigate.mockReset();
    mockUseAuth.mockReset();
    mockPushToast.mockReset();
    mockApiPost.mockReset();
    mockPushApiErrorToast.mockReset();
    delete window.PublicKeyCredential;
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
    window.localStorage.clear();
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = false;
    vi.clearAllMocks();
  });

  it('renders the anomaly banner as a floating overlay and restores a remembered email', async () => {
    window.localStorage.setItem('caps_ai_login_email', 'remembered@example.com');

    await renderPage({
      loginAnomaly: {
        new_device: true,
        new_network: false,
        message: 'We noticed a login from a new device.'
      }
    });

    const banner = document.querySelector('[data-testid="anomaly-alert-banner"]');
    const emailInput = document.querySelector('input[name="email"]');

    expect(banner).not.toBeNull();
    expect(banner.className).toContain('fixed');
    expect(banner.className).toContain('top-4');
    expect(emailInput.value).toBe('remembered@example.com');
    expect(document.body.textContent).toContain('Review Activity');
    expect(document.body.textContent).toContain('Secure Account');
  });

  it('renders the SMS MFA branch and supports resending the login challenge', async () => {
    const login = vi.fn().mockResolvedValue({
      mfaRequired: true,
      pendingMfaToken: 'pending-123',
      mfaMethods: ['sms'],
      primaryMethod: 'sms',
      challenge: {
        method: 'sms',
        challenge_sent: true,
        phone_number_masked: '+*******4567',
        expires_in_seconds: 300,
        resend_after_seconds: 30
      }
    });
    mockApiPost.mockResolvedValue({
      data: {
        method: 'sms',
        challenge_sent: true,
        phone_number_masked: '+*******4567',
        expires_in_seconds: 300,
        resend_after_seconds: 30
      }
    });

    await renderPage({ login });
    await fillAndSubmitPrimaryLogin();

    expect(document.body.textContent).toContain('Multi-factor verification required');
    expect(document.body.textContent).toContain('SMS challenge sent to +*******4567');
    expect(document.body.textContent).toContain('Code expires after 5 minutes.');
    expect(document.body.textContent).toContain('Resend is available every 30 seconds.');

    const resendButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Resend SMS code')
    );
    expect(resendButton).not.toBeNull();

    await act(async () => {
      resendButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(mockApiPost).toHaveBeenCalledWith('/auth/mfa/sms/challenge/resend', {
      pending_mfa_token: 'pending-123'
    });
    expect(mockPushToast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Code sent',
        variant: 'success'
      })
    );
  });

  it('shows a WebAuthn unsupported-browser error during MFA verification', async () => {
    const login = vi.fn().mockResolvedValue({
      mfaRequired: true,
      pendingMfaToken: 'pending-webauthn',
      mfaMethods: ['webauthn'],
      primaryMethod: 'webauthn',
      challenge: null
    });

    await renderPage({ login });
    await fillAndSubmitPrimaryLogin();

    const submitButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Continue with Passkey')
    );
    expect(submitButton).not.toBeNull();

    await act(async () => {
      submitButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await waitForTick();
      await waitForTick();
    });

    expect(document.body.textContent).toContain('This browser does not support WebAuthn passkeys/security keys.');
  });

  it('prefers the last successful MFA method when it is still available', async () => {
    window.localStorage.setItem('caps_ai_last_mfa_method', 'webauthn');
    const login = vi.fn().mockResolvedValue({
      mfaRequired: true,
      pendingMfaToken: 'pending-preferred-method',
      mfaMethods: ['sms', 'webauthn'],
      primaryMethod: 'sms',
      challenge: null
    });

    await renderPage({ login });
    await fillAndSubmitPrimaryLogin();

    expect(document.body.textContent).toContain('Passkeys are not available in this browser');
    expect(document.body.textContent).toContain('Continue with Passkey');
  });
});
