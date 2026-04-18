import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  Fingerprint,
  GraduationCap,
  LifeBuoy,
  Lock,
  Mail,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  Timer
} from 'lucide-react';
import { motion } from 'framer-motion';
import Card from '../components/ui/Card';
import { PasswordStrengthMeter } from '../components/auth/PasswordStrengthMeter';
import { AnomalyAlertBanner } from '../components/auth/AnomalyAlertBanner';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/apiClient';
import { pushApiErrorToast } from '../utils/errorToast';
import { formatApiError } from '../utils/apiError';

const REMEMBERED_EMAIL_KEY = 'caps_ai_login_email';
const LAST_MFA_METHOD_KEY = 'caps_ai_last_mfa_method';

function readLocalStorageValue(key) {
  if (typeof window === 'undefined') {
    return '';
  }
  try {
    return window.localStorage.getItem(key) || '';
  } catch {
    return '';
  }
}

function writeLocalStorageValue(key, value) {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures on restricted browsers.
  }
}

function removeLocalStorageValue(key) {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore storage failures on restricted browsers.
  }
}

function resolveGoogleAuthUrl() {
  const directUrl = import.meta.env.VITE_GOOGLE_AUTH_URL?.trim();
  if (directUrl) return directUrl;

  const clientId = import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID?.trim();
  const redirectUri = import.meta.env.VITE_GOOGLE_OAUTH_REDIRECT_URI?.trim();
  if (!clientId || !redirectUri) return '';

  const scope = import.meta.env.VITE_GOOGLE_OAUTH_SCOPE?.trim() || 'openid email profile';
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope,
    access_type: 'offline',
    prompt: 'select_account'
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

const KNOWN_MFA_METHODS = ['totp', 'sms', 'webauthn', 'backup'];

function normalizeMfaMethod(method) {
  if (!method || typeof method !== 'string') {
    return null;
  }
  const normalized = method.trim().toLowerCase();
  const aliases = {
    app: 'totp',
    authenticator: 'totp',
    authenticator_app: 'totp',
    text: 'sms',
    passkey: 'webauthn',
    security_key: 'webauthn',
    backup_code: 'backup'
  };
  const mapped = aliases[normalized] || normalized;
  return KNOWN_MFA_METHODS.includes(mapped) ? mapped : null;
}

function normalizeMfaMethods(methods) {
  if (!Array.isArray(methods)) {
    return [];
  }
  return methods
    .map((method) => normalizeMfaMethod(method))
    .filter((method, index, list) => method && list.indexOf(method) === index);
}

function formatDurationLabel(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) {
    return '';
  }
  if (value < 60) {
    return `${value} second${value === 1 ? '' : 's'}`;
  }
  const minutes = Math.ceil(value / 60);
  return `${minutes} minute${minutes === 1 ? '' : 's'}`;
}

const MFA_METHOD_META = {
  totp: {
    label: 'Authenticator App',
    shortLabel: 'Authenticator',
    description: 'Open your authenticator app and enter the current 6-digit code.',
    inputLabel: 'Authenticator Code',
    placeholder: '000000',
    Icon: Smartphone,
    accent: 'from-sky-400 to-cyan-300'
  },
  sms: {
    label: 'SMS Code',
    shortLabel: 'SMS',
    description: 'Use the one-time text message sent to your verified phone.',
    inputLabel: 'SMS Verification Code',
    placeholder: '000000',
    Icon: MessageSquare,
    accent: 'from-blue-400 to-indigo-300'
  },
  webauthn: {
    label: 'Passkey / Security Key',
    shortLabel: 'Passkey',
    description: 'Approve the browser prompt with Touch ID, Windows Hello, or a registered security key.',
    inputLabel: 'Passkey prompt',
    placeholder: '',
    Icon: Fingerprint,
    accent: 'from-emerald-300 to-teal-300'
  },
  backup: {
    label: 'Backup Code',
    shortLabel: 'Backup',
    description: 'Use a saved recovery code if your primary device is unavailable.',
    inputLabel: 'Backup Code',
    placeholder: 'Enter backup code',
    Icon: LifeBuoy,
    accent: 'from-amber-300 to-orange-300'
  }
};

export default function LoginPage() {
  const navigate = useNavigate();
  const {
    login,
    completeMfaLogin,
    beginWebAuthnMfaLogin,
    completeWebAuthnMfaLogin,
    isAuthenticated,
    checking,
    loginAnomaly
  } = useAuth();
  const { pushToast } = useToast();
  const googleAuthUrl = resolveGoogleAuthUrl();
  const [form, setForm] = useState(() => ({
    email: readLocalStorageValue(REMEMBERED_EMAIL_KEY),
    password: ''
  }));
  const [rememberEmail, setRememberEmail] = useState(() => Boolean(readLocalStorageValue(REMEMBERED_EMAIL_KEY)));
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mfaState, setMfaState] = useState(null);
  const [mfaMethod, setMfaMethod] = useState('totp');
  const [mfaCode, setMfaCode] = useState('');
  const [mfaSubmitting, setMfaSubmitting] = useState(false);
  const [smsChallenge, setSmsChallenge] = useState(null);
  const [showAnomaly, setShowAnomaly] = useState(Boolean(loginAnomaly));
  const [showAlternativeSignIn, setShowAlternativeSignIn] = useState(false);
  const [capsLockOn, setCapsLockOn] = useState(false);
  const [showSlowSignInHint, setShowSlowSignInHint] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({ email: '', password: '' });

  const mfaMethodOptions = useMemo(() => {
    if (!mfaState) {
      return [];
    }
    const gathered = new Set();
    for (const method of mfaState.methods || []) {
      const normalized = normalizeMfaMethod(method);
      if (normalized) {
        gathered.add(normalized);
      }
    }
    const primary = normalizeMfaMethod(mfaState.primaryMethod);
    if (primary) {
      gathered.add(primary);
    }
    const challengeMethod = normalizeMfaMethod(smsChallenge?.method);
    if (challengeMethod) {
      gathered.add(challengeMethod);
    }
    const selected = normalizeMfaMethod(mfaMethod);
    if (selected) {
      gathered.add(selected);
    }

    // Present known methods in consistent order and always keep backup as fallback.
    const ordered = ['totp', 'sms', 'webauthn'].filter((method) => gathered.has(method));
    ordered.push('backup');
    return ordered;
  }, [mfaMethod, mfaState, smsChallenge]);

  const activeMfaMeta = MFA_METHOD_META[mfaMethod] || MFA_METHOD_META.totp;
  const ActiveMfaIcon = activeMfaMeta.Icon;
  const primaryMfaMethod = normalizeMfaMethod(mfaState?.primaryMethod);
  const smsExpiryLabel = formatDurationLabel(smsChallenge?.expires_in_seconds);
  const smsResendLabel = formatDurationLabel(smsChallenge?.resend_after_seconds);
  const webAuthnAvailable = typeof window !== 'undefined' && Boolean(window.PublicKeyCredential);

  useEffect(() => {
    if (loginAnomaly) {
      setShowAnomaly(true);
    }
  }, [loginAnomaly]);

  useEffect(() => {
    if (!loading) {
      setShowSlowSignInHint(false);
      return undefined;
    }
    const timeoutId = window.setTimeout(() => {
      setShowSlowSignInHint(true);
    }, 2500);
    return () => window.clearTimeout(timeoutId);
  }, [loading]);

  useEffect(() => {
    if (!checking && isAuthenticated) {
      globalThis.location.replace('/dashboard');
    }
  }, [checking, isAuthenticated]);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (name === 'email' || name === 'password') {
      setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    }
  }

  function validateEmail(value) {
    const email = value.trim();
    if (!email) {
      return 'Enter your work email address.';
    }
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email) ? '' : 'Enter a valid email address.';
  }

  function validatePassword(value) {
    return value.trim() ? '' : 'Enter your password to continue.';
  }

  function handleFieldBlur(event) {
    const { name, value } = event.target;
    if (name === 'email') {
      setFieldErrors((prev) => ({ ...prev, email: validateEmail(value) }));
      return;
    }
    if (name === 'password') {
      setFieldErrors((prev) => ({ ...prev, password: validatePassword(value) }));
    }
  }

  function handlePasswordKeyEvent(event) {
    if (typeof event.getModifierState === 'function') {
      setCapsLockOn(event.getModifierState('CapsLock'));
    }
  }

  function persistRememberedEmail(email) {
    const trimmedEmail = email.trim();
    if (rememberEmail && trimmedEmail) {
      writeLocalStorageValue(REMEMBERED_EMAIL_KEY, trimmedEmail);
      return;
    }
    removeLocalStorageValue(REMEMBERED_EMAIL_KEY);
  }

  async function onSubmit(event) {
    event.preventDefault();
    const submittedEmail = event.currentTarget?.elements?.email?.value ?? form.email;
    const submittedPassword = event.currentTarget?.elements?.password?.value ?? form.password;
    const normalizedEmail = String(submittedEmail || '').trim();
    const normalizedPassword = String(submittedPassword || '');

    if (normalizedEmail !== form.email || normalizedPassword !== form.password) {
      setForm((prev) => ({
        ...prev,
        email: normalizedEmail,
        password: normalizedPassword
      }));
    }

    const nextFieldErrors = {
      email: validateEmail(normalizedEmail),
      password: validatePassword(normalizedPassword)
    };
    setFieldErrors(nextFieldErrors);
    if (nextFieldErrors.email || nextFieldErrors.password) {
      setError('Fix highlighted fields before signing in.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const loginResult = await login(normalizedEmail, normalizedPassword);
      if (loginResult?.mfaRequired) {
        const methods = normalizeMfaMethods(loginResult?.mfaMethods || []);
        const challengeMethod = normalizeMfaMethod(loginResult?.challenge?.method);
        const primaryMethod =
          normalizeMfaMethod(loginResult?.primaryMethod) ||
          challengeMethod ||
          methods[0] ||
          'totp';
        const mergedMethods = [...new Set([...methods, ...(challengeMethod ? [challengeMethod] : []), primaryMethod])]
          .filter((method) => method && method !== 'backup');
        const rememberedMfaMethod = normalizeMfaMethod(readLocalStorageValue(LAST_MFA_METHOD_KEY));
        const preferredMethod =
          rememberedMfaMethod && rememberedMfaMethod !== 'backup' && mergedMethods.includes(rememberedMfaMethod)
            ? rememberedMfaMethod
            : primaryMethod;
        setMfaState({
          pendingMfaToken: loginResult.pendingMfaToken,
          methods: mergedMethods,
          primaryMethod
        });
        setMfaMethod(preferredMethod);
        setMfaCode('');
        setSmsChallenge(loginResult?.challenge || null);
        persistRememberedEmail(normalizedEmail);
        pushToast({
          title: 'Additional verification required',
          description: 'Complete MFA to finish signing in.',
          variant: 'info'
        });
      } else {
        persistRememberedEmail(normalizedEmail);
        pushToast({ title: 'Welcome back', description: 'Login successful.', variant: 'success' });
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      if (err.response?.status === 423) {
        const lockedMessage = err.response?.data?.detail || 'Account temporarily locked. Try again later.';
        setError(lockedMessage);
        pushToast({
          title: 'Account Locked',
          description: 'Too many failed login attempts. Please try again later.',
          variant: 'error'
        });
      } else {
        const detail = err?.response?.data?.detail || 'Login failed';
        setError(formatApiError(err, String(detail)));
        pushApiErrorToast(pushToast, err, 'Login failed');
      }
    } finally {
      setLoading(false);
    }
  }

  async function requestSmsChallenge({ resend }) {
    if (!mfaState?.pendingMfaToken) {
      return;
    }
    const endpoint = resend ? '/auth/mfa/sms/challenge/resend' : '/auth/mfa/sms/challenge/send';
    const response = await apiClient.post(endpoint, {
      pending_mfa_token: mfaState.pendingMfaToken
    });
    setSmsChallenge(response.data);
    return response.data;
  }

  async function verifyWebAuthn() {
    if (!mfaState?.pendingMfaToken) {
      return;
    }
    if (!window.PublicKeyCredential) {
      throw new Error('This browser does not support WebAuthn passkeys/security keys.');
    }
    const { startAuthentication } = await import('@simplewebauthn/browser');
    const begin = await beginWebAuthnMfaLogin(mfaState.pendingMfaToken);
    const credential = await startAuthentication(begin.options);
    await completeWebAuthnMfaLogin({
      pendingMfaToken: mfaState.pendingMfaToken,
      credential
    });
  }

  async function onSubmitMfa(event) {
    event.preventDefault();
    if (!mfaState?.pendingMfaToken) {
      return;
    }

    setError('');
    setMfaSubmitting(true);
    try {
      if (mfaMethod === 'webauthn') {
        await verifyWebAuthn();
      } else {
        if (!mfaCode.trim()) {
          setError('Enter your verification code to continue.');
          return;
        }
        if (mfaMethod === 'backup' && /^\d{6}$/.test(mfaCode.trim())) {
          setError('Backup codes are not 6-digit OTPs. Use a saved backup code or switch verification method.');
          return;
        }
        await completeMfaLogin({
          pendingMfaToken: mfaState.pendingMfaToken,
          method: mfaMethod,
          code: mfaCode.trim()
        });
      }

      if (mfaMethod !== 'backup') {
        writeLocalStorageValue(LAST_MFA_METHOD_KEY, mfaMethod);
      }
      persistRememberedEmail(form.email);
      setMfaState(null);
      setMfaCode('');
      setSmsChallenge(null);
      pushToast({ title: 'Verification complete', description: 'Login successful.', variant: 'success' });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'MFA verification failed';
      const detailText = String(detail).toLowerCase();
      if (detailText.includes('method is not enabled')) {
        const fallbackMethod = mfaMethodOptions.find((method) => method !== 'backup');
        if (fallbackMethod && fallbackMethod !== mfaMethod) {
          setMfaMethod(fallbackMethod);
          setMfaCode('');
        }
      }
      setError(formatApiError(err, String(detail)));
      pushApiErrorToast(pushToast, err, 'MFA verification failed');
    } finally {
      setMfaSubmitting(false);
    }
  }

  async function onResendSms() {
    setError('');
    setMfaSubmitting(true);
    try {
      const challenge = await requestSmsChallenge({ resend: true });
      pushToast({
        title: 'Code sent',
        description: challenge?.phone_number_masked
          ? `A new SMS code was sent to ${challenge.phone_number_masked}.`
          : 'A new SMS code was sent.',
        variant: 'success'
      });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Could not resend SMS code';
      setError(formatApiError(err, String(detail)));
      pushApiErrorToast(pushToast, err, 'Could not resend SMS code');
    } finally {
      setMfaSubmitting(false);
    }
  }

  useEffect(() => {
    if (!mfaState?.pendingMfaToken) {
      return;
    }
    if (mfaMethod !== 'sms' || smsChallenge?.challenge_sent) {
      return;
    }
    requestSmsChallenge({ resend: false }).catch(() => {
      // Error is surfaced when the user attempts to continue.
    });
  }, [mfaMethod, mfaState, smsChallenge]);

  function onGoogleClick() {
    if (googleAuthUrl) {
      globalThis.location.assign(googleAuthUrl);
      return;
    }
    pushToast({
      title: 'Google sign-in unavailable',
      description: 'Set VITE_GOOGLE_AUTH_URL or VITE_GOOGLE_OAUTH_CLIENT_ID + VITE_GOOGLE_OAUTH_REDIRECT_URI.',
      variant: 'info'
    });
  }

  function handleReviewActivity() {
    navigate(isAuthenticated ? '/history' : '/auth/forgot-password');
  }

  function handleSecureAccount() {
    navigate(isAuthenticated ? '/profile?tab=security' : '/auth/forgot-password');
  }

  return (
    <main className="relative min-h-[100dvh] overflow-hidden bg-[#f4f7fb] text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <AnomalyAlertBanner
        anomaly={showAnomaly ? loginAnomaly : null}
        onDismiss={() => setShowAnomaly(false)}
        onReviewActivity={handleReviewActivity}
        onSecureAccount={handleSecureAccount}
        floating
      />

      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-28 top-0 h-80 w-80 rounded-full bg-cyan-300/20 blur-3xl dark:bg-cyan-900/40" />
        <div className="absolute right-0 top-10 h-96 w-96 rounded-full bg-indigo-300/25 blur-3xl dark:bg-indigo-900/35" />
        <div className="absolute bottom-[-8rem] left-1/3 h-80 w-80 rounded-full bg-brand-200/35 blur-3xl dark:bg-brand-900/30" />
        <div
          className="absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(15,23,42,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(15,23,42,0.05) 1px, transparent 1px)',
            backgroundSize: '44px 44px'
          }}
        />
      </div>

      <section className="relative z-10 mx-auto grid min-h-[100dvh] w-full max-w-[1200px] grid-cols-1 items-center gap-8 px-6 py-8 sm:px-8 lg:grid-cols-12 lg:gap-10 lg:px-12 lg:py-12">
        <motion.aside
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          className="hidden h-full flex-col justify-between rounded-[28px] border border-white/70 bg-white/72 p-8 shadow-[0_26px_70px_-48px_rgba(15,23,42,0.44)] backdrop-blur-xl dark:border-slate-800 dark:bg-slate-900/70 lg:col-span-5 lg:flex"
        >
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-white px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-700 dark:border-brand-900 dark:bg-slate-900 dark:text-brand-300">
              <Building2 size={14} />
              SaaS Admin Workspace
            </div>

            <div className="space-y-4">
              <h1 className="text-4xl font-semibold tracking-tight text-slate-950 dark:text-white">
                Secure access for operations,
                <span className="block text-brand-700 dark:text-brand-300">analytics, and classroom intelligence.</span>
              </h1>
              <p className="max-w-md text-sm leading-7 text-slate-600 dark:text-slate-300">
                Continue into CAPS AI with institution-grade authentication, role-aware controls, and encrypted traffic end to end.
              </p>
            </div>

            <div className="grid gap-3">
              {[
                'Role-based sessions for admins, teachers, and staff',
                '2-step verification with authenticator, SMS, passkey, and backup',
                'Audit-ready authentication events for every sign-in'
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center gap-3 rounded-2xl border border-slate-200/70 bg-white/85 px-4 py-3 text-sm text-slate-700 shadow-sm dark:border-slate-800 dark:bg-slate-900/80 dark:text-slate-200"
                >
                  <CheckCircle2 size={16} className="shrink-0 text-emerald-500" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200/70 bg-white/90 p-4 dark:border-slate-800 dark:bg-slate-950/70">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Trust & Compliance</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">SOC 2 Ready</span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">TLS Encrypted</span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">MFA Enforced</span>
            </div>
          </div>
        </motion.aside>

        <div className="lg:col-span-7 lg:justify-self-end">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, ease: 'easeOut' }}
            className="w-full max-w-[540px]"
          >
            <Card className="!rounded-[26px] !border-slate-200/80 !bg-white/95 !p-0 !shadow-[0_28px_70px_-40px_rgba(15,23,42,0.45)] dark:!border-slate-800 dark:!bg-slate-900/92">
              <div className="space-y-6 p-6 sm:p-8">
                <header className="space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.15em] text-brand-700 dark:text-brand-300">
                        {mfaState ? 'Step 2 of 2' : 'Secure Sign-In'}
                      </p>
                      <h1 className="mt-2 text-[1.75rem] font-semibold tracking-tight text-slate-950 dark:text-white">
                        {mfaState ? 'Security check' : 'Welcome Back'}
                      </h1>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                        {mfaState ? 'One quick verification to finish signing in' : 'Sign in to your CAPS AI account'}
                      </p>
                    </div>
                    <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-cyan-500 text-white shadow-lg shadow-brand-500/20">
                      {mfaState ? <ShieldCheck size={22} /> : <GraduationCap size={22} />}
                    </div>
                  </div>

                  <div className="grid gap-2 rounded-2xl border border-slate-200/80 bg-slate-50/85 p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-950/70 dark:text-slate-300 sm:grid-cols-3">
                    <span className="inline-flex items-center gap-1.5"><ShieldCheck size={14} className="text-emerald-500" /> Encrypted connection</span>
                    <span className="inline-flex items-center gap-1.5"><Lock size={14} className="text-brand-500" /> Protected credentials</span>
                    <span className="inline-flex items-center gap-1.5"><Timer size={14} className="text-cyan-500" /> Session monitoring</span>
                  </div>
                </header>

                {!mfaState ? (
                  <>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50/40 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:border-brand-700 dark:hover:bg-brand-950/30"
                      onClick={() => setShowAlternativeSignIn((current) => !current)}
                      aria-expanded={showAlternativeSignIn}
                      aria-controls="alternative-signin-options"
                    >
                      <span>More sign-in options</span>
                      <ChevronDown size={16} className={`transition-transform ${showAlternativeSignIn ? 'rotate-180' : ''}`} />
                    </button>

                    {showAlternativeSignIn ? (
                      <div id="alternative-signin-options" className="space-y-3 rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-950/70">
                        <button
                          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:border-brand-200 hover:bg-brand-50/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-brand-700"
                          type="button"
                          onClick={onGoogleClick}
                        >
                          <span className="grid h-5 w-5 place-items-center rounded-full bg-white text-[11px] font-bold text-brand-600 shadow-sm">G</span>
                          Continue with Google
                        </button>
                        <button
                          className="flex w-full items-center justify-between rounded-xl border border-dashed border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
                          type="button"
                          disabled
                          title="Enable passwordless OTP with your administrator"
                        >
                          <span>OTP Sign-In (optional)</span>
                          <span className="text-[11px] font-semibold uppercase tracking-[0.12em]">Planned</span>
                        </button>
                      </div>
                    ) : null}
                  </>
                ) : null}

                {!mfaState ? (
                  <form className="space-y-5" onSubmit={onSubmit} noValidate>
                    <div className="space-y-2">
                      <label htmlFor="email" className="text-sm font-semibold text-slate-700 dark:text-slate-200">Work Email</label>
                      <div className="group relative">
                        <Mail className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-brand-500" size={18} aria-hidden="true" />
                        <input
                          id="email"
                          className={`w-full rounded-xl border bg-white py-3.5 pl-11 pr-4 text-sm text-slate-900 outline-none transition ${fieldErrors.email ? 'border-rose-400 focus:border-rose-500 focus:ring-2 focus:ring-rose-100' : 'border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-100'} dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-brand-900/50`}
                          name="email"
                          type="email"
                          autoComplete="email"
                          placeholder="name@institution.edu"
                          required
                          autoFocus
                          value={form.email}
                          onChange={onChange}
                          onBlur={handleFieldBlur}
                          aria-label="Email address"
                          aria-invalid={Boolean(fieldErrors.email)}
                        />
                      </div>
                      {fieldErrors.email ? <p className="text-xs text-rose-600 dark:text-rose-300">{fieldErrors.email}</p> : null}
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label htmlFor="password" className="text-sm font-semibold text-slate-700 dark:text-slate-200">Password</label>
                        <button
                          className="text-xs font-semibold text-brand-700 transition-colors hover:text-brand-600 dark:text-brand-300 dark:hover:text-brand-200"
                          type="button"
                          onClick={() => navigate('/auth/forgot-password')}
                          aria-label="Go to forgot password page"
                        >
                          Forgot password?
                        </button>
                      </div>

                      <div className="group relative">
                        <Lock className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-brand-500" size={18} aria-hidden="true" />
                        <input
                          id="password"
                          className={`w-full rounded-xl border bg-white py-3.5 pl-11 pr-12 text-sm text-slate-900 outline-none transition ${fieldErrors.password ? 'border-rose-400 focus:border-rose-500 focus:ring-2 focus:ring-rose-100' : 'border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-100'} dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-brand-900/50`}
                          name="password"
                          type={showPassword ? 'text' : 'password'}
                          autoComplete="current-password"
                          placeholder="Enter your password"
                          required
                          value={form.password}
                          onChange={onChange}
                          onBlur={handleFieldBlur}
                          onKeyUp={handlePasswordKeyEvent}
                          onKeyDown={handlePasswordKeyEvent}
                          aria-label="Password"
                          aria-invalid={Boolean(fieldErrors.password)}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword((current) => !current)}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-brand-600 dark:hover:bg-slate-800 dark:hover:text-brand-300"
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                        >
                          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>

                      {capsLockOn ? (
                        <p className="inline-flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-300">
                          <AlertTriangle size={14} /> Caps Lock is on.
                        </p>
                      ) : null}
                      {fieldErrors.password ? <p className="text-xs text-rose-600 dark:text-rose-300">{fieldErrors.password}</p> : null}
                      <PasswordStrengthMeter password={form.password} userInputs={[form.email]} />
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50 px-3.5 py-3 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-300">
                      <label className="inline-flex items-center gap-2.5">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                          checked={rememberEmail}
                          onChange={(event) => {
                            const nextChecked = event.target.checked;
                            setRememberEmail(nextChecked);
                            if (!nextChecked) {
                              removeLocalStorageValue(REMEMBERED_EMAIL_KEY);
                            }
                          }}
                        />
                        <span>Remember me on this device</span>
                      </label>
                      <span className="text-xs text-slate-500 dark:text-slate-400">Avoid this on shared devices</span>
                    </div>

                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      transition={{ duration: 0.16 }}
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-500 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-600/25 transition disabled:cursor-not-allowed disabled:opacity-60"
                      type="submit"
                      disabled={loading || !form.email.trim() || !form.password.trim()}
                    >
                      <span>{loading ? 'Signing in...' : 'Sign In'}</span>
                      {!loading ? <ArrowRight size={18} /> : null}
                    </motion.button>

                    {showSlowSignInHint ? (
                      <p className="text-center text-xs text-slate-500 dark:text-slate-400">Still signing you in. Secure verification can take a few extra seconds.</p>
                    ) : null}

                    <div className="grid gap-2 rounded-xl border border-slate-200/80 bg-white p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-300">
                      <span className="inline-flex items-center gap-1.5"><ShieldCheck size={14} className="text-emerald-500" /> Your credentials are never stored in plain text.</span>
                      <span className="inline-flex items-center gap-1.5"><Lock size={14} className="text-brand-500" /> Sign-in attempts are rate-limited and monitored.</span>
                    </div>
                  </form>
                ) : (
                  <form className="space-y-5" onSubmit={onSubmitMfa}>
                    <div className="rounded-2xl border border-brand-200 bg-brand-50/70 p-4 text-brand-950 dark:border-brand-900 dark:bg-brand-950/30 dark:text-brand-100">
                      <div className="flex items-start gap-3">
                        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white shadow-sm dark:bg-slate-900">
                          <ShieldCheck size={18} className="text-brand-600 dark:text-brand-300" />
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-700 dark:text-brand-300">Step 2 of 2</p>
                          <p className="mt-1 text-base font-semibold">Multi-factor verification required</p>
                          <p className="mt-1 text-sm text-brand-900/80 dark:text-brand-100/85">Choose an available method below. We will only finish login after this check succeeds.</p>
                        </div>
                      </div>

                      {smsChallenge?.phone_number_masked ? (
                        <p className="mt-3 rounded-xl border border-brand-200 bg-white/70 px-3 py-2 text-xs font-medium text-brand-800 dark:border-brand-900 dark:bg-slate-900/70 dark:text-brand-100">
                          SMS challenge sent to {smsChallenge.phone_number_masked}
                        </p>
                      ) : null}

                      {mfaMethod === 'sms' && (smsExpiryLabel || smsResendLabel) ? (
                        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                          {smsExpiryLabel ? (
                            <span className="inline-flex items-center gap-1.5 rounded-xl border border-brand-200/60 bg-white/75 px-3 py-2 dark:border-brand-900 dark:bg-slate-900/70">
                              <Timer size={13} /> Code expires after {smsExpiryLabel}.
                            </span>
                          ) : null}
                          {smsResendLabel ? (
                            <span className="inline-flex items-center gap-1.5 rounded-xl border border-brand-200/60 bg-white/75 px-3 py-2 dark:border-brand-900 dark:bg-slate-900/70">
                              <RefreshCw size={13} /> Resend is available every {smsResendLabel}.
                            </span>
                          ) : null}
                        </div>
                      ) : null}

                      {mfaMethod === 'sms' && smsChallenge?.error ? (
                        <p className="mt-3 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/70 dark:bg-amber-900/20 dark:text-amber-200">
                          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                          <span>SMS delivery issue: {smsChallenge.error}</span>
                        </p>
                      ) : null}
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Verification Method</label>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400">Use any active method</span>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        {mfaMethodOptions.map((method) => {
                          const selected = mfaMethod === method;
                          const methodMeta = MFA_METHOD_META[method] || MFA_METHOD_META.totp;
                          const Icon = methodMeta.Icon;

                          return (
                            <button
                              key={method}
                              type="button"
                              onClick={() => {
                                setMfaMethod(method);
                                setMfaCode('');
                              }}
                              className={`rounded-xl border px-3 py-2.5 text-left transition ${selected ? 'border-brand-400 bg-brand-50 text-brand-900 shadow-sm dark:border-brand-700 dark:bg-brand-950/30 dark:text-brand-100' : 'border-slate-200 bg-white text-slate-700 hover:border-brand-200 hover:bg-brand-50/40 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:border-brand-700 dark:hover:bg-brand-950/20'}`}
                            >
                              <span className="flex items-center gap-2.5">
                                <span className={`grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br ${methodMeta.accent} text-slate-950`}>
                                  <Icon size={16} />
                                </span>
                                <span className="min-w-0">
                                  <span className="block text-xs font-semibold sm:text-sm">{methodMeta.shortLabel}</span>
                                  <span className="block truncate text-[10px] text-slate-500 dark:text-slate-400">
                                    {primaryMfaMethod === method ? 'Primary method' : methodMeta.label}
                                  </span>
                                </span>
                                {selected ? <CheckCircle2 size={15} className="ml-auto text-brand-600 dark:text-brand-300" /> : null}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/70">
                      <div className="flex items-start gap-3">
                        <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br ${activeMfaMeta.accent} text-slate-950`}>
                          <ActiveMfaIcon size={17} />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{activeMfaMeta.label}</p>
                          <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-300">{activeMfaMeta.description}</p>
                        </div>
                      </div>
                    </div>

                    {mfaMethod === 'webauthn' ? (
                      <div className={`rounded-xl border p-4 text-sm ${webAuthnAvailable ? 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/20 dark:text-emerald-100' : 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/20 dark:text-amber-100'}`}>
                        <p className="flex items-center gap-2 font-semibold">
                          {webAuthnAvailable ? <Fingerprint size={16} /> : <AlertTriangle size={16} />}
                          {webAuthnAvailable ? 'Ready for browser prompt' : 'Passkeys are not available in this browser'}
                        </p>
                        <p className="mt-1 text-xs opacity-90">
                          {webAuthnAvailable
                            ? 'Press continue and approve the system prompt when it appears.'
                            : 'Switch to a browser with WebAuthn support, or choose authenticator, SMS, or backup code.'}
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <label htmlFor="mfa_code" className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                          {activeMfaMeta.inputLabel}
                        </label>
                        <input
                          id="mfa_code"
                          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-center font-mono text-xl tracking-[0.24em] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-brand-900/50"
                          type="text"
                          inputMode={mfaMethod === 'backup' ? 'text' : 'numeric'}
                          maxLength={mfaMethod === 'backup' ? 24 : 6}
                          placeholder={activeMfaMeta.placeholder}
                          value={mfaCode}
                          onChange={(event) => {
                            const raw = event.target.value;
                            setMfaCode(mfaMethod === 'backup' ? raw.trim() : raw.replace(/\D/g, ''));
                          }}
                        />
                        {mfaMethod === 'backup' ? (
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            Use one of your saved backup codes from MFA setup. Backup codes are not 6-digit authenticator OTPs.
                          </p>
                        ) : null}
                      </div>
                    )}

                    {mfaMethod === 'sms' ? (
                      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-950/70">
                        <span className="text-xs text-slate-600 dark:text-slate-300">Did not receive it? Check your signal, then resend.</span>
                        <button
                          type="button"
                          onClick={onResendSms}
                          disabled={mfaSubmitting}
                          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold text-brand-700 transition-colors hover:bg-brand-50 hover:text-brand-600 disabled:opacity-60 dark:text-brand-300 dark:hover:bg-brand-950/30 dark:hover:text-brand-200"
                        >
                          <RefreshCw size={13} />
                          Resend SMS code
                        </button>
                      </div>
                    ) : null}

                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      transition={{ duration: 0.16 }}
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-500 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-600/25 transition disabled:cursor-not-allowed disabled:opacity-60"
                      type="submit"
                      disabled={mfaSubmitting || (mfaMethod !== 'webauthn' && !mfaCode.trim())}
                    >
                      <span>{mfaSubmitting ? 'Verifying...' : mfaMethod === 'webauthn' ? 'Continue with Passkey' : 'Verify and Continue'}</span>
                      {!mfaSubmitting ? <ArrowRight size={18} /> : null}
                    </motion.button>
                  </form>
                )}

                {error ? (
                  <motion.p
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/35 dark:text-rose-300"
                    role="status"
                    aria-live="assertive"
                  >
                    {error}
                  </motion.p>
                ) : null}

                <footer className="space-y-3 border-t border-slate-200/80 pt-4 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <p>
                    User provisioning is managed by your administrator. Secure access via CAPS AI infrastructure.
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => navigate('/register')}
                      className="font-semibold text-brand-700 hover:text-brand-600 dark:text-brand-300 dark:hover:text-brand-200"
                    >
                      Request new account
                    </button>
                    <span aria-hidden="true">•</span>
                    <button
                      type="button"
                      onClick={() => navigate('/auth/forgot-password')}
                      className="font-semibold text-brand-700 hover:text-brand-600 dark:text-brand-300 dark:hover:text-brand-200"
                    >
                      Need help signing in?
                    </button>
                  </div>
                </footer>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>
    </main>
  );
}
