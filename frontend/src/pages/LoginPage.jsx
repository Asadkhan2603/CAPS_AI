import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, GraduationCap, Lock, Mail } from 'lucide-react';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { pushToast } = useToast();
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
      pushToast({ title: 'Login failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  function onGoogleClick() {
    pushToast({
      title: 'Google sign-in unavailable',
      description: 'OAuth login is not configured yet.',
      variant: 'info'
    });
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-100 p-4">
      <section className="w-full max-w-[420px] space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-sky-600 text-white shadow-soft">
            <GraduationCap size={28} />
          </div>
          <h1 className="text-5 text-4xl font-bold text-slate-900">Welcome Back</h1>
          <p className="mt-1 text-slate-600">Sign in to your CAPS AI account</p>
        </div>

        <Card className="space-y-5 !rounded-2xl !border !border-slate-200 !bg-white !p-6">
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
            Don&apos;t have an account?{' '}
            <Link className="font-semibold text-sky-700 hover:text-sky-800" to="/register">
              Register here
            </Link>
          </div>
        </Card>
      </section>
    </main>
  );
}
