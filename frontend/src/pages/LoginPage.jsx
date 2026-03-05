import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, GraduationCap, Lock, Mail, Sparkles } from 'lucide-react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
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
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 20 });
  const x1 = useTransform(springX, (value) => value);
  const y1 = useTransform(springY, (value) => value);
  const x2 = useTransform(springX, (value) => value * -1.5);
  const y2 = useTransform(springY, (value) => value * -1.5);
  const x3 = useTransform(springX, (value) => value * 0.8);
  const y3 = useTransform(springY, (value) => value * 1.2);

  useEffect(() => {
    function handleMouseMove(event) {
      const { clientX, clientY } = event;
      const { innerWidth, innerHeight } = window;
      mouseX.set((clientX / innerWidth - 0.5) * 50);
      mouseY.set((clientY / innerHeight - 0.5) * 50);
    }

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

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
    <main className="auth-shell relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute inset-0 z-0">
        <div className="auth-wallpaper" />
        <motion.div
          style={{ x: x1, y: y1 }}
          animate={{ scale: [1, 1.1, 1], rotate: [0, 5, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="auth-orb left-[-10%] top-[-10%] h-[600px] w-[600px] bg-cyan-500/10 blur-[120px]"
        />
        <motion.div
          style={{ x: x2, y: y2 }}
          animate={{ scale: [1, 1.2, 1], rotate: [0, -5, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="auth-orb right-[-5%] top-[20%] h-[500px] w-[500px] bg-blue-600/10 blur-[100px]"
        />
        <motion.div
          style={{ x: x3, y: y3 }}
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
          className="auth-orb bottom-[-10%] left-[20%] h-[550px] w-[550px] bg-indigo-500/10 blur-[110px]"
        />
      </div>

      <section className="relative z-10 mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.aside
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="auth-hero hidden space-y-8 lg:block"
        >
          <div className="space-y-4">
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-sky-300 backdrop-blur-md"
            >
              <Sparkles size={14} className="animate-pulse" />
              CAPS AI Portal
            </motion.p>
            <h1 className="text-5xl font-bold leading-[1.1] tracking-tight text-white">
              Welcome back.
              <br />
              <span className="bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
                Build smarter classrooms.
              </span>
            </h1>
            <p className="max-w-xl text-lg leading-relaxed text-slate-300/90">
              Access attendance, timetable, evaluations, and AI-assisted workflows from one secure dashboard.
            </p>
          </div>

          <div className="grid gap-4">
            {[
              'Role-aware access for admins, teachers, and students.',
              'Live API + analytics modules with secure token sessions.',
              'Designed for institution-scale operations on AKS.'
            ].map((text, index) => (
              <motion.div
                key={text}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + index * 0.1 }}
                className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm transition-colors hover:bg-white/[0.06]"
              >
                <div className="h-2 w-2 rounded-full bg-sky-500 transition-transform group-hover:scale-150" />
                <span className="text-sm text-slate-200">{text}</span>
              </motion.div>
            ))}
          </div>
        </motion.aside>

        <div className="w-full max-w-[460px] justify-self-center lg:justify-self-end">
          <motion.div
            initial={{ opacity: 0, y: 40, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="mb-8 text-center lg:hidden">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 260, damping: 20, delay: 0.3 }}
                className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20"
              >
                <GraduationCap size={32} />
              </motion.div>
              <h1 className="text-3xl font-bold text-white">Welcome Back</h1>
              <p className="mt-2 text-slate-400">Sign in to your CAPS AI account</p>
            </div>

            <Card className="auth-card overflow-hidden !rounded-[2.5rem] !border-white/20 !bg-white/10 !shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] !backdrop-blur-2xl">
              <div className="space-y-7 p-8 sm:p-10">
                <div className="hidden space-y-2 text-center lg:block">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 20, delay: 0.3 }}
                    className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20"
                  >
                    <GraduationCap size={32} />
                  </motion.div>
                  <h1 className="text-3xl font-bold text-white">Welcome Back</h1>
                  <p className="text-slate-400">Sign in to your CAPS AI account</p>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02, backgroundColor: 'rgba(255,255,255,0.15)' }}
                  whileTap={{ scale: 0.98 }}
                  className="flex w-full items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/10 py-3.5 text-sm font-semibold text-white backdrop-blur-md transition-all"
                  type="button"
                  onClick={onGoogleClick}
                >
                  <div className="grid h-6 w-6 place-items-center rounded-full bg-white text-xs font-bold text-sky-600">G</div>
                  Continue with Google
                </motion.button>

                <div className="flex items-center gap-4 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                  <span className="h-px flex-1 bg-white/10" />
                  or email
                  <span className="h-px flex-1 bg-white/10" />
                </div>

                <form className="space-y-5" onSubmit={onSubmit}>
                  <div className="space-y-2">
                    <label className="ml-1 text-xs font-bold uppercase tracking-wider text-slate-400">Email Address</label>
                    <div className="group relative">
                      <Mail
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-sky-400"
                        size={18}
                      />
                      <input
                        className="w-full rounded-2xl border border-white/10 bg-white/5 py-4 pl-12 pr-4 text-sm text-white outline-none transition-all placeholder:text-slate-600 focus:border-sky-500/50 focus:bg-white/10 focus:ring-4 focus:ring-sky-500/10"
                        name="email"
                        type="email"
                        placeholder="name@university.edu"
                        required
                        value={form.email}
                        onChange={onChange}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="ml-1 flex items-center justify-between">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Password</label>
                      <button className="text-xs font-semibold text-sky-400 transition-colors hover:text-sky-300" type="button" onClick={onGoogleClick}>
                        Forgot?
                      </button>
                    </div>
                    <div className="group relative">
                      <Lock
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-sky-400"
                        size={18}
                      />
                      <input
                        className="w-full rounded-2xl border border-white/10 bg-white/5 py-4 pl-12 pr-4 text-sm text-white outline-none transition-all placeholder:text-slate-600 focus:border-sky-500/50 focus:bg-white/10 focus:ring-4 focus:ring-sky-500/10"
                        name="password"
                        type="password"
                        placeholder="********"
                        required
                        value={form.password}
                        onChange={onChange}
                      />
                    </div>
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.03, filter: 'brightness(1.1)', boxShadow: '0 0 25px rgba(14, 165, 233, 0.5)' }}
                    whileTap={{ scale: 0.97 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                    className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-500 to-indigo-600 py-4 text-sm font-bold text-white shadow-lg transition-all disabled:cursor-not-allowed disabled:opacity-50"
                    type="submit"
                    disabled={loading}
                  >
                    <span>{loading ? 'Signing in...' : 'Sign In'}</span>
                    {!loading ? <ArrowRight size={18} /> : null}
                  </motion.button>
                </form>

                {error ? (
                  <motion.p
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-center text-xs font-medium text-rose-400"
                  >
                    {error}
                  </motion.p>
                ) : null}

                <p className="text-center text-[11px] font-medium leading-relaxed text-slate-500">
                  User provisioning is managed by your administrator.
                  <br />
                  Secure access via CAPS AI Infrastructure.
                </p>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>
    </main>
  );
}
