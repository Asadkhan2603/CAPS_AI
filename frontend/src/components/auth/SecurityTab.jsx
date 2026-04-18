import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { startRegistration } from '@simplewebauthn/browser';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  KeyRound,
  Lock,
  RefreshCw,
  Shield,
  Smartphone,
  ToggleRight
} from 'lucide-react';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../hooks/useToast';
import Card from '../ui/Card';

function logSecurityDiagnostic(message, error) {
  if (import.meta.env.DEV) {
    console.error(message, error);
  }
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

export const SecurityTab = () => {
  const [securitySettings, setSecuritySettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [totpSetup, setTotpSetup] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const [smsPhoneNumber, setSmsPhoneNumber] = useState('');
  const [smsVerificationCode, setSmsVerificationCode] = useState('');
  const [smsPending, setSmsPending] = useState(null);
  const [webauthnLabel, setWebauthnLabel] = useState('');
  const [activeSetupMethod, setActiveSetupMethod] = useState(null);
  const [browserSupportsWebAuthn, setBrowserSupportsWebAuthn] = useState(false);
  const { pushToast } = useToast();

  useEffect(() => {
    fetchSecuritySettings();
    setBrowserSupportsWebAuthn(Boolean(window.PublicKeyCredential));
  }, []);

  const fetchSecuritySettings = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/auth/security-settings/me');
      setSecuritySettings(response.data);
    } catch (err) {
      logSecurityDiagnostic('Failed to load security settings:', err);
      setSecuritySettings({
        mfa_enabled: false,
        mfa_methods: [],
        primary_method: null,
        method_status: {
          sms: {
            enabled: false,
            ready: false,
            phone_number_masked: null,
            delivery_configured: true,
            resend_after_seconds: 0,
            expires_in_seconds: 0
          },
          webauthn: {
            enabled: false,
            ready: false,
            credential_count: 0
          }
        },
        webauthn_credentials: [],
        password_strength: 'strong',
        password_last_changed: new Date().toISOString(),
        sessions_active: 1,
        recovery_codes_remaining: 0
      });
      pushToast({
        title: 'Security settings unavailable',
        description: 'Showing fallback values because the latest settings could not be loaded.',
        variant: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const isMethodEnabled = (method) => securitySettings?.mfa_methods?.includes(method);

  const getStrengthColor = (strength) => {
    switch (strength) {
      case 'weak':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'fair':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'good':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'strong':
        return 'text-green-600 bg-green-50 border-green-200';
      default:
        return 'text-slate-600 bg-slate-50 border-slate-200';
    }
  };

  const startTotpSetup = async () => {
    setUpdating(true);
    try {
      const response = await apiClient.post('/auth/mfa/totp/enable');
      setTotpSetup(response.data);
      setTotpCode('');
      pushToast({
        title: 'Authenticator setup started',
        description: 'Scan the QR code and enter the current 6-digit code from your app.',
        variant: 'success'
      });
    } catch (err) {
      logSecurityDiagnostic('Failed to start TOTP setup:', err);
      pushToast({
        title: 'MFA setup failed',
        description: err?.response?.data?.detail || 'Could not start authenticator app setup.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const confirmTotpSetup = async () => {
    if (!totpCode.match(/^\d{6}$/)) {
      pushToast({
        title: 'Invalid code',
        description: 'Enter the 6-digit code from your authenticator app.',
        variant: 'error'
      });
      return;
    }

    setUpdating(true);
    try {
      await apiClient.post('/auth/mfa/totp/confirm', { otp_code: totpCode });
      setTotpSetup(null);
      setTotpCode('');
      await fetchSecuritySettings();
      pushToast({
        title: 'MFA enabled',
        description: 'Authenticator app protection is now active for your account.',
        variant: 'success'
      });
    } catch (err) {
      logSecurityDiagnostic('Failed to confirm TOTP setup:', err);
      pushToast({
        title: 'Verification failed',
        description: err?.response?.data?.detail || 'The authenticator code was not accepted.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const disableTotp = async () => {
    setUpdating(true);
    try {
      await apiClient.post('/auth/mfa/totp/disable');
      setTotpSetup(null);
      setTotpCode('');
      await fetchSecuritySettings();
      pushToast({
        title: 'MFA disabled',
        description: 'Authenticator app protection has been turned off.',
        variant: 'info'
      });
    } catch (err) {
      logSecurityDiagnostic('Failed to disable TOTP:', err);
      pushToast({
        title: 'Disable failed',
        description: err?.response?.data?.detail || 'Could not disable authenticator app MFA.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const sendSmsEnrollmentCode = async () => {
    if (!smsPhoneNumber.trim()) {
      pushToast({
        title: 'Phone number required',
        description: 'Enter your phone number in international format (e.g. +15551234567).',
        variant: 'error'
      });
      return;
    }

    setUpdating(true);
    try {
      const response = await apiClient.post('/auth/mfa/sms/enroll/send', {
        phone_number: smsPhoneNumber
      });
      setSmsPending(response.data);
      pushToast({
        title: 'Verification code sent',
        description: response.data.phone_number_masked
          ? `Code sent to ${response.data.phone_number_masked}.`
          : 'Check your phone for the verification code.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Could not send SMS code',
        description: err?.response?.data?.detail || 'SMS delivery failed or is not configured.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const verifySmsEnrollment = async () => {
    if (!smsVerificationCode.match(/^\d{6}$/)) {
      pushToast({
        title: 'Invalid code',
        description: 'Enter the 6-digit SMS verification code.',
        variant: 'error'
      });
      return;
    }

    setUpdating(true);
    try {
      await apiClient.post('/auth/mfa/sms/enroll/verify', {
        otp_code: smsVerificationCode
      });
      setSmsPhoneNumber('');
      setSmsVerificationCode('');
      setSmsPending(null);
      await fetchSecuritySettings();
      pushToast({
        title: 'SMS MFA enabled',
        description: 'SMS verification is now active for login.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Verification failed',
        description: err?.response?.data?.detail || 'Could not verify the SMS code.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const disableSms = async () => {
    setUpdating(true);
    try {
      await apiClient.post('/auth/mfa/sms/disable');
      await fetchSecuritySettings();
      setSmsPending(null);
      setSmsVerificationCode('');
      pushToast({
        title: 'SMS MFA disabled',
        description: 'SMS verification has been turned off.',
        variant: 'info'
      });
    } catch (err) {
      pushToast({
        title: 'Disable failed',
        description: err?.response?.data?.detail || 'Could not disable SMS MFA.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const registerWebAuthnCredential = async () => {
    if (!browserSupportsWebAuthn) {
      pushToast({
        title: 'WebAuthn not supported',
        description: 'This browser does not support passkeys/security keys.',
        variant: 'error'
      });
      return;
    }

    setUpdating(true);
    try {
      const begin = await apiClient.post('/auth/mfa/webauthn/register/begin', {
        label: webauthnLabel.trim() || undefined
      });
      const credential = await startRegistration(begin.data.options);
      await apiClient.post('/auth/mfa/webauthn/register/finish', {
        credential,
        label: webauthnLabel.trim() || undefined
      });
      setWebauthnLabel('');
      await fetchSecuritySettings();
      pushToast({
        title: 'WebAuthn enabled',
        description: 'Your passkey/security key was registered successfully.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'WebAuthn setup failed',
        description: err?.response?.data?.detail || err?.message || 'Could not complete WebAuthn registration.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const removeWebAuthnCredential = async (credentialId) => {
    setUpdating(true);
    try {
      await apiClient.delete(`/auth/mfa/webauthn/credentials/${encodeURIComponent(credentialId)}`);
      await fetchSecuritySettings();
      pushToast({
        title: 'Credential removed',
        description: 'WebAuthn credential removed successfully.',
        variant: 'info'
      });
    } catch (err) {
      pushToast({
        title: 'Remove failed',
        description: err?.response?.data?.detail || 'Could not remove WebAuthn credential.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const disableWebAuthn = async () => {
    setUpdating(true);
    try {
      await apiClient.post('/auth/mfa/webauthn/disable');
      await fetchSecuritySettings();
      pushToast({
        title: 'WebAuthn disabled',
        description: 'All registered passkeys/security keys were removed.',
        variant: 'info'
      });
    } catch (err) {
      pushToast({
        title: 'Disable failed',
        description: err?.response?.data?.detail || 'Could not disable WebAuthn MFA.',
        variant: 'error'
      });
    } finally {
      setUpdating(false);
    }
  };

  const handleMethodClick = async (method) => {
    if (method === 'totp') {
      setActiveSetupMethod(null);
      if (isMethodEnabled('totp')) {
        await disableTotp();
      } else {
        await startTotpSetup();
      }
      return;
    }

    if (method === 'sms' && isMethodEnabled('sms')) {
      setActiveSetupMethod(null);
      await disableSms();
      return;
    }

    if (method === 'sms') {
      setActiveSetupMethod((current) => (current === 'sms' ? null : 'sms'));
      return;
    }

    if (method === 'webauthn' && isMethodEnabled('webauthn')) {
      setActiveSetupMethod(null);
      await disableWebAuthn();
      return;
    }

    if (method === 'webauthn') {
      setActiveSetupMethod((current) => (current === 'webauthn' ? null : 'webauthn'));
    }
  };

  const cancelTotpSetup = () => {
    setTotpSetup(null);
    setTotpCode('');
  };

  const renderMethodStatus = (method) => {
    if (isMethodEnabled(method)) {
      return (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-green-600 dark:text-green-400">
          <CheckCircle className="w-3 h-3" /> Enabled
        </p>
      );
    }

    if (method === 'totp' && totpSetup) {
      return (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400">
          <RefreshCw className="w-3 h-3" /> Awaiting verification
        </p>
      );
    }

    if (method === 'webauthn' && !browserSupportsWebAuthn) {
      return (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-amber-600 dark:text-amber-400">
          <AlertTriangle className="w-3 h-3" /> Browser does not support WebAuthn
        </p>
      );
    }

    return null;
  };

  const renderMethodButtonLabel = (method) => {
    if (method === 'totp' && totpSetup) {
      return 'Setup in progress';
    }
    if (!isMethodEnabled(method) && activeSetupMethod === method) {
      return 'Close setup';
    }
    if (isMethodEnabled(method)) {
      return 'Disable';
    }
    return 'Set up';
  };

  const renderMethodButtonClassName = (method) => {
    return isMethodEnabled(method)
      ? 'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-950 dark:text-red-400 dark:hover:bg-red-900'
      : 'bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-950 dark:text-blue-400 dark:hover:bg-blue-900';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const backupCodes = totpSetup?.backup_codes || [];
  const smsStatus = securitySettings?.method_status?.sms || {};
  const webauthnCredentials = securitySettings?.webauthn_credentials || [];
  const smsMaskedPhone = smsPending?.phone_number_masked || smsStatus.phone_number_masked;
  const smsExpiryLabel = formatDurationLabel(smsPending?.expires_in_seconds || smsStatus.expires_in_seconds);
  const smsResendLabel = formatDurationLabel(smsPending?.resend_after_seconds || smsStatus.resend_after_seconds);

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-lg font-semibold">
            <Shield className="h-5 w-5 text-blue-600" />
            Security Overview
          </h3>
          <button
            onClick={fetchSecuritySettings}
            className="rounded-lg p-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            title="Refresh security settings"
          >
            <RefreshCw className="h-4 w-4 text-slate-600" />
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <motion.div
            className={`rounded-lg border p-4 ${
              securitySettings?.mfa_enabled
                ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
                : 'bg-yellow-50 border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800'
            }`}
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                  2-Factor Authentication
                </p>
                <p className="mt-2 text-sm font-bold">
                  {securitySettings?.mfa_enabled ? 'Enabled' : 'Disabled'}
                </p>
              </div>
              {securitySettings?.mfa_enabled ? (
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              )}
            </div>
          </motion.div>

          <motion.div
            className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                  Active Sessions
                </p>
                <p className="mt-2 text-3xl font-bold text-blue-600 dark:text-blue-400">
                  {securitySettings?.sessions_active || 1}
                </p>
              </div>
              <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
          </motion.div>

          <motion.div
            className={`rounded-lg border p-4 ${getStrengthColor(securitySettings?.password_strength)}`}
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                  Password Strength
                </p>
                <p className="mt-2 text-sm font-bold capitalize">
                  {securitySettings?.password_strength || 'Strong'}
                </p>
              </div>
              <Lock className="h-5 w-5" />
            </div>
          </motion.div>

          <motion.div
            className={`rounded-lg border p-4 ${
              securitySettings?.recovery_codes_remaining > 3
                ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
                : 'bg-orange-50 border-orange-200 dark:bg-orange-950 dark:border-orange-800'
            }`}
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                  Recovery Codes
                </p>
                <p className="mt-2 text-3xl font-bold">
                  {securitySettings?.recovery_codes_remaining || 0}
                </p>
              </div>
              <CheckCircle className="h-5 w-5" />
            </div>
          </motion.div>
        </div>
      </Card>

      <Card className="overflow-hidden !p-0">
        <div className="relative overflow-hidden border-b border-slate-200 bg-slate-950 p-5 text-white dark:border-slate-800">
          <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-cyan-400/20 blur-3xl" />
          <div className="absolute -bottom-24 left-16 h-56 w-56 rounded-full bg-emerald-400/10 blur-3xl" />
          <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-100">
                <Shield className="h-3.5 w-3.5" />
                MFA Control Center
              </p>
              <h3 className="mt-4 text-2xl font-bold tracking-tight">Multi-Factor Authentication</h3>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Configure trusted login methods from one production path. This page reads only from the security-settings payload, so status, setup, and removal stay aligned with login enforcement.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2 rounded-2xl border border-white/10 bg-white/10 p-2 text-center backdrop-blur">
              <div className="rounded-xl bg-white/10 px-3 py-2">
                <p className="text-lg font-bold">{securitySettings?.mfa_enabled ? 'On' : 'Off'}</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-300">MFA</p>
              </div>
              <div className="rounded-xl bg-white/10 px-3 py-2">
                <p className="text-lg font-bold">{securitySettings?.mfa_methods?.length || 0}</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-300">Methods</p>
              </div>
              <div className="rounded-xl bg-white/10 px-3 py-2">
                <p className="text-lg font-bold">{securitySettings?.recovery_codes_remaining || 0}</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-300">Backup</p>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-4 sm:p-5">
          <div className="rounded-2xl border border-cyan-200 bg-cyan-50/70 p-4 dark:border-cyan-950 dark:bg-cyan-950/30">
            <p className="text-sm font-semibold text-cyan-950 dark:text-cyan-100">Production MFA contract</p>
            <p className="mt-1 text-sm text-cyan-900/75 dark:text-cyan-200/75">
              Configure one or more MFA methods. Login enforcement and settings use the same backend MFA status contract.
            </p>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
          <motion.div
            className="flex h-full flex-col justify-between rounded-3xl border border-sky-200 bg-gradient-to-br from-white to-sky-50/80 p-4 shadow-[0_18px_55px_-38px_rgba(2,132,199,0.65)] transition-colors hover:border-sky-300 dark:border-sky-900 dark:from-slate-950 dark:to-sky-950/35"
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-start gap-3">
              <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl bg-sky-600 text-white shadow-lg shadow-sky-600/20">
                <Smartphone className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-slate-900 dark:text-white">Authenticator App</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Use Google Authenticator, Authy, Microsoft Authenticator, or another TOTP app.
                </p>
                {renderMethodStatus('totp')}
              </div>
            </div>
            <motion.button
              onClick={() => handleMethodClick('totp')}
              disabled={updating}
              aria-label={`${renderMethodButtonLabel('totp')} Authenticator App MFA`}
              className={`mt-4 flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-2.5 font-semibold transition-colors ${renderMethodButtonClassName(
                'totp'
              )}`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <ToggleRight className="h-4 w-4" />
              {renderMethodButtonLabel('totp')}
            </motion.button>
          </motion.div>

          <motion.div
            className="flex h-full flex-col justify-between rounded-3xl border border-indigo-200 bg-gradient-to-br from-white to-indigo-50/80 p-4 shadow-[0_18px_55px_-38px_rgba(79,70,229,0.65)] transition-colors hover:border-indigo-300 dark:border-indigo-900 dark:from-slate-950 dark:to-indigo-950/35"
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-start gap-3">
              <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/20">
                <Lock className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-slate-900 dark:text-white">SMS Text Message</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Receive one-time codes via SMS after the phone verification flow is completed.
                </p>
                {smsStatus.phone_number_masked && isMethodEnabled('sms') ? (
                  <p className="mt-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                    Verified number: {smsStatus.phone_number_masked}
                  </p>
                ) : null}
                {smsExpiryLabel || smsResendLabel ? (
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    {smsExpiryLabel ? `Codes expire after ${smsExpiryLabel}. ` : ''}
                    {smsResendLabel ? `You can request another code every ${smsResendLabel}.` : ''}
                  </p>
                ) : null}
                {!smsStatus.delivery_configured ? (
                  <p className="mt-2 text-xs font-semibold text-amber-600 dark:text-amber-400">
                    SMS delivery is not fully configured. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and either
                    `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID` before using SMS in production.
                  </p>
                ) : null}
                {renderMethodStatus('sms')}
              </div>
            </div>
            <motion.button
              onClick={() => handleMethodClick('sms')}
              disabled={updating}
              aria-label={`${renderMethodButtonLabel('sms')} SMS Text Message MFA`}
              className={`mt-4 flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-2.5 font-semibold transition-colors ${renderMethodButtonClassName(
                'sms'
              )}`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <ToggleRight className="h-4 w-4" />
              {renderMethodButtonLabel('sms')}
            </motion.button>
          </motion.div>

          <motion.div
            className="flex h-full flex-col justify-between rounded-3xl border border-emerald-200 bg-gradient-to-br from-white to-emerald-50/80 p-4 shadow-[0_18px_55px_-38px_rgba(16,185,129,0.65)] transition-colors hover:border-emerald-300 dark:border-emerald-900 dark:from-slate-950 dark:to-emerald-950/35"
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-start gap-3">
              <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl bg-emerald-600 text-white shadow-lg shadow-emerald-600/20">
                <Shield className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-slate-900 dark:text-white">Security Key / Biometric</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Register platform passkeys or roaming security keys with WebAuthn.
                </p>
                {securitySettings?.method_status?.webauthn?.credential_count ? (
                  <p className="mt-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                    Registered credentials: {securitySettings.method_status.webauthn.credential_count}
                  </p>
                ) : null}
                {renderMethodStatus('webauthn')}
              </div>
            </div>
            <motion.button
              onClick={() => handleMethodClick('webauthn')}
              disabled={updating}
              aria-label={`${renderMethodButtonLabel('webauthn')} Security Key MFA`}
              className={`mt-4 flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-2.5 font-semibold transition-colors ${renderMethodButtonClassName(
                'webauthn'
              )}`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <ToggleRight className="h-4 w-4" />
              {renderMethodButtonLabel('webauthn')}
            </motion.button>
          </motion.div>
        </div>

        {!isMethodEnabled('sms') && activeSetupMethod === 'sms' ? (
          <div className="rounded-3xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-4 shadow-[0_18px_60px_-42px_rgba(79,70,229,0.7)] dark:border-indigo-900 dark:from-indigo-950/40 dark:to-slate-950">
            <p className="text-base font-bold text-indigo-950 dark:text-indigo-100">Set up SMS verification</p>
            <p className="mt-1 text-sm text-indigo-800 dark:text-indigo-200">
              Enter a phone number, send a code, then verify it to enable SMS at login.
            </p>
            {!smsStatus.delivery_configured ? (
              <p className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                SMS delivery is not configured yet. The backend must have Twilio credentials before real messages can send.
              </p>
            ) : null}
            <div className="mt-3 grid gap-3 sm:grid-cols-[1fr,auto]">
              <label className="block">
                <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">
                  Phone number
                </span>
                <input
                  type="tel"
                  value={smsPhoneNumber}
                  onChange={(event) => setSmsPhoneNumber(event.target.value)}
                  placeholder="Example: +15551234567"
                  autoFocus
                  className="w-full rounded-2xl border border-indigo-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-indigo-300 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 dark:border-indigo-900 dark:bg-slate-950 dark:text-white dark:placeholder:text-indigo-500/60 dark:focus:ring-indigo-950"
                />
              </label>
              <button
                onClick={sendSmsEnrollmentCode}
                disabled={updating}
                className="self-end rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-700 disabled:opacity-60"
              >
                {updating ? 'Sending...' : smsPending ? 'Resend code' : 'Send code'}
              </button>
            </div>

            {smsMaskedPhone || smsExpiryLabel || smsResendLabel ? (
              <div className="mt-3 rounded-lg border border-indigo-200 bg-white/70 px-3 py-2 text-xs text-indigo-900 dark:border-indigo-900 dark:bg-slate-900/60 dark:text-indigo-100">
                {smsMaskedPhone ? <p>Masked destination: {smsMaskedPhone}</p> : null}
                {smsExpiryLabel ? <p>Code expiry: {smsExpiryLabel}</p> : null}
                {smsResendLabel ? <p>Resend cooldown: {smsResendLabel}</p> : null}
              </div>
            ) : null}

            {smsPending ? (
              <div className="mt-3 grid gap-3 sm:grid-cols-[1fr,auto]">
                <label className="block">
                  <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">
                    Verification code
                  </span>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength="6"
                    value={smsVerificationCode}
                    onChange={(event) => setSmsVerificationCode(event.target.value.replace(/\D/g, ''))}
                    placeholder="Enter 6-digit code"
                    className="w-full rounded-2xl border border-indigo-200 bg-white px-4 py-3 text-center font-mono text-xl tracking-[0.2em] text-slate-900 outline-none transition placeholder:text-indigo-300 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 dark:border-indigo-900 dark:bg-slate-950 dark:text-white dark:placeholder:text-indigo-500/60 dark:focus:ring-indigo-950"
                  />
                </label>
                <button
                  onClick={verifySmsEnrollment}
                  disabled={updating || smsVerificationCode.length !== 6}
                  className="self-end rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-700 disabled:opacity-60"
                >
                  {updating ? 'Verifying...' : 'Verify'}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}

        {!isMethodEnabled('webauthn') && activeSetupMethod === 'webauthn' ? (
          <div className="rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-4 shadow-[0_18px_60px_-42px_rgba(16,185,129,0.7)] dark:border-emerald-900 dark:from-emerald-950/40 dark:to-slate-950">
            <p className="flex items-center gap-2 text-base font-bold text-emerald-950 dark:text-emerald-100">
              <KeyRound className="h-4 w-4" /> WebAuthn Registration
            </p>
            <p className="mt-1 text-sm text-emerald-800 dark:text-emerald-200">
              Name this passkey or security key so it is easy to recognize later.
            </p>
            {!browserSupportsWebAuthn ? (
              <p className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                Browser does not support WebAuthn. Try Chrome, Edge, Safari, or Firefox with passkey support enabled.
              </p>
            ) : null}
            <div className="mt-3 grid gap-3 sm:grid-cols-[1fr,auto]">
              <label className="block">
                <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
                  Credential label
                </span>
                <input
                  type="text"
                  value={webauthnLabel}
                  onChange={(event) => setWebauthnLabel(event.target.value)}
                  placeholder="Example: Work laptop"
                  autoFocus
                  className="w-full rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-emerald-300 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 dark:border-emerald-900 dark:bg-slate-950 dark:text-white dark:placeholder:text-emerald-500/60 dark:focus:ring-emerald-950"
                />
              </label>
              <button
                onClick={registerWebAuthnCredential}
                disabled={updating || !browserSupportsWebAuthn}
                className="self-end rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-600/20 hover:bg-emerald-700 disabled:opacity-60"
              >
                {updating ? 'Registering...' : 'Register'}
              </button>
            </div>
          </div>
        ) : null}

        {webauthnCredentials.length > 0 ? (
          <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
            <p className="text-sm font-semibold text-slate-900 dark:text-white">Registered WebAuthn Credentials</p>
            <div className="mt-3 space-y-2">
              {webauthnCredentials.map((credential) => (
                <div
                  key={credential.credential_id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
                >
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{credential.label || 'Authenticator'}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Last used: {credential.last_used_at ? new Date(credential.last_used_at).toLocaleString() : 'Never'}
                    </p>
                  </div>
                  <button
                    onClick={() => removeWebAuthnCredential(credential.credential_id)}
                    disabled={updating}
                    className="rounded border border-red-300 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-60 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {totpSetup && (
          <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 dark:border-blue-900 dark:bg-blue-950/40">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                  Finish authenticator app setup
                </p>
                <p className="mt-1 text-sm text-blue-800 dark:text-blue-200">
                  Scan the QR code, store the backup codes, then enter the current 6-digit code from your app to activate MFA.
                </p>
              </div>
              <button
                onClick={cancelTotpSetup}
                disabled={updating}
                className="text-sm font-medium text-blue-700 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100"
              >
                Cancel
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-[220px,1fr]">
              <div className="rounded-lg bg-white p-3 shadow-sm dark:bg-slate-900">
                <img src={totpSetup.qr_code} alt="MFA QR code" className="mx-auto h-48 w-48" />
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-blue-200 bg-white p-3 dark:border-blue-900 dark:bg-slate-900">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Manual setup key
                  </p>
                  <code className="mt-2 block break-all text-sm text-slate-800 dark:text-slate-200">
                    {totpSetup.secret}
                  </code>
                </div>

                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
                  <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">
                    Backup codes
                  </p>
                  <p className="mt-1 text-xs text-amber-800 dark:text-amber-200">
                    Save these now. Each code can be used once if you lose access to your authenticator app.
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {backupCodes.map((code) => (
                      <code
                        key={code}
                        className="rounded bg-white px-3 py-2 text-sm text-slate-800 shadow-sm dark:bg-slate-900 dark:text-slate-200"
                      >
                        {code}
                      </code>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Verification code
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength="6"
                    value={totpCode}
                    onChange={(event) => setTotpCode(event.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                    disabled={updating}
                    className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-center text-2xl font-mono focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={confirmTotpSetup}
                    disabled={updating || totpCode.length !== 6}
                    className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {updating ? 'Verifying...' : 'Verify and enable'}
                  </button>
                  <button
                    onClick={cancelTotpSetup}
                    disabled={updating}
                    className="rounded-lg border border-slate-300 px-4 py-2 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
                  >
                    Cancel setup
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        </div>
      </Card>

      <Card className="space-y-4">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <Lock className="h-5 w-5 text-slate-600" />
          Password Information
        </h3>

        <div className="space-y-3">
          <div className="flex items-center justify-between rounded-lg border border-slate-200 p-4 dark:border-slate-700">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Last Changed</p>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                {securitySettings?.password_last_changed
                  ? new Date(securitySettings.password_last_changed).toLocaleDateString()
                  : 'Never'}
              </p>
            </div>
            <Clock className="h-5 w-5 text-slate-400" />
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              <strong>Tip:</strong> Change your password regularly and keep your backup codes somewhere safe offline.
            </p>
          </div>
        </div>
      </Card>

      <Card className="space-y-3 border-l-4 border-l-blue-500">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <Activity className="h-5 w-5 text-blue-600" />
          Recommendation
        </h3>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Review your <strong>Account Activity Dashboard</strong> regularly to monitor login attempts and active sessions. Disable any unfamiliar devices immediately.
        </p>
      </Card>
    </div>
  );
};

export default SecurityTab;
