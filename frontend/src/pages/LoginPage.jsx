import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, GraduationCap, Lock, Mail, Sparkles } from 'lucide-react';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { pushApiErrorToast } from '../utils/errorToast';

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

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { pushToast } = useToast();
  const googleAuthUrl = resolveGoogleAuthUrl();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.email, form.password);
      pushToast({ title: 'Welcome back', description: 'Login successful.', variant: 'success' });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Login failed';
      setError(String(detail));
      pushApiErrorToast(pushToast, err, 'Login failed');
    } finally {
      setLoading(false);
    }
  }

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

  return (
    <main className="auth-shell p-4">
      <div className="auth-wallpaper" />
      <div className="auth-orb left-[-120px] top-[-120px] h-[340px] w-[340px] bg-cyan-400/55" />
      <div className="auth-orb right-[-100px] top-1/3 h-[300px] w-[300px] bg-blue-500/50 [animation-delay:1.2s]" />
      <div className="auth-orb bottom-[-140px] left-1/3 h-[360px] w-[360px] bg-sky-300/35 [animation-delay:2.5s]" />

      <section className="relative z-10 mx-auto grid w-full max-w-5xl items-center gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <aside className="auth-hero auth-reveal hidden lg:block">
          <p className="inline-flex items-center gap-2 rounded-full border border-sky-300/35 bg-sky-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-200">
            <Sparkles size={14} />
            CAPS AI Portal
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight">Welcome back. Build smarter classrooms with clarity.</h1>
          <p className="mt-4 max-w-xl text-sm leading-7 text-slate-200/90">
            Access attendance, timetable, evaluations, and AI-assisted workflows from one secure dashboard.
          </p>
          <div className="mt-7 grid gap-3 text-sm">
            <div className="rounded-2xl border border-white/15 bg-white/[0.05] p-3">Role-aware access for admins, teachers, and students.</div>
            <div className="rounded-2xl border border-white/15 bg-white/[0.05] p-3">Live API + analytics modules with secure token sessions.</div>
            <div className="rounded-2xl border border-white/15 bg-white/[0.05] p-3">Designed for institution-scale operations on AKS.</div>
          </div>
        </aside>

        <div className="w-full max-w-[440px] justify-self-center auth-reveal lg:justify-self-end">
          <div className="mb-4 text-center lg:hidden">
            <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-sky-600 text-white shadow-soft">
              <GraduationCap size={24} />
            </div>
            <h1 className="text-3xl font-bold text-slate-100">Welcome Back</h1>
            <p className="mt-1 text-sm text-slate-300">Sign in to your CAPS AI account</p>
          </div>

          <Card className="auth-card space-y-5 !rounded-3xl !p-6 sm:!p-7">
            <div className="hidden text-center lg:block">
              <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-sky-600 text-white shadow-soft">
                <GraduationCap size={24} />
              </div>
              <h1 className="text-3xl font-bold text-slate-900">Welcome Back</h1>
              <p className="mt-1 text-sm text-slate-600">Sign in to your CAPS AI account</p>
            </div>

            <button className="btn-secondary w-full !justify-center !py-3" type="button" onClick={onGoogleClick}>
              <span className="mr-2 grid h-5 w-5 place-items-center rounded-full bg-white text-sm font-bold text-sky-600 shadow">G</span>
              Continue with Google
            </button>

            <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              <span className="h-px flex-1 bg-slate-200" />
              or continue with email
              <span className="h-px flex-1 bg-slate-200" />
            </div>

            <form className="space-y-4" onSubmit={onSubmit}>
              <label className="block space-y-1">
                <span className="text-sm font-medium text-slate-700">Email Address</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                  <input
                    className="input w-full !pl-10"
                    name="email"
                    type="email"
                    placeholder="name@university.edu"
                    required
                    value={form.email}
                    onChange={onChange}
                  />
                </div>
              </label>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700">Password</span>
                  <button className="text-xs font-medium text-sky-700 hover:text-sky-800" type="button" onClick={onGoogleClick}>
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                  <input
                    className="input w-full !pl-10"
                    name="password"
                    type="password"
                    placeholder="********"
                    required
                    value={form.password}
                    onChange={onChange}
                  />
                </div>
              </div>

              <button className="btn-primary w-full !justify-center !bg-sky-600 !py-3 hover:!bg-sky-700" type="submit" disabled={loading}>
                <span>{loading ? 'Signing in...' : 'Sign In'}</span>
                <ArrowRight size={16} />
              </button>
            </form>

            {error ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p> : null}

            <div className="border-t border-slate-200 pt-4 text-center text-sm text-slate-600">
              User provisioning is managed by your administrator.
            </div>
          </Card>
        </div>
      </section>
    </main>
  );
}
