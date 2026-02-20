import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
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

  return (
    <main className="grid min-h-screen place-items-center bg-gradient-to-br from-brand-50 via-slate-50 to-sky-100 p-4 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <Card className="w-full max-w-md space-y-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-brand-500">CAPS AI</p>
          <h1 className="mt-1 text-2xl font-semibold">Sign in to your workspace</h1>
        </div>

        <form className="space-y-3" onSubmit={onSubmit}>
          <FormInput label="Email" name="email" type="email" required value={form.email} onChange={onChange} />
          <FormInput label="Password" name="password" type="password" required value={form.password} onChange={onChange} />
          <button className="btn-primary w-full" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {error ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600 dark:bg-rose-900/20 dark:text-rose-300">{error}</p> : null}

        <p className="text-sm text-slate-600 dark:text-slate-300">
          New to CAPS AI? <Link className="font-medium text-brand-600" to="/register">Create account</Link>
        </p>
      </Card>
    </main>
  );
}
