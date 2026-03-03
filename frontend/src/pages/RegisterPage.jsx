import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GraduationCap, ShieldCheck } from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, login } = useAuth();
  const { pushToast } = useToast();
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'admin',
    admin_type: 'super_admin'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await register(form);
      await login(form.email, form.password);
      pushToast({ title: 'Bootstrap complete', description: 'Super admin created successfully.', variant: 'success' });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Registration failed';
      setError(String(detail));
      pushToast({ title: 'Registration failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell p-4">
      <div className="auth-wallpaper" />
      <div className="auth-orb left-[-120px] top-[-120px] h-[340px] w-[340px] bg-cyan-400/50" />
      <div className="auth-orb right-[-100px] top-1/3 h-[300px] w-[300px] bg-blue-500/45 [animation-delay:1.2s]" />
      <div className="auth-orb bottom-[-140px] left-1/3 h-[360px] w-[360px] bg-sky-300/30 [animation-delay:2.5s]" />

      <section className="relative z-10 mx-auto grid w-full max-w-5xl items-center gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <aside className="auth-hero auth-reveal hidden lg:block">
          <p className="inline-flex items-center gap-2 rounded-full border border-sky-300/35 bg-sky-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-200">
            <ShieldCheck size={14} />
            Bootstrap Control
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight">Initialize secure administration in one guided step.</h1>
          <p className="mt-4 max-w-xl text-sm leading-7 text-slate-200/90">
            This route is bootstrap-only. After setup, user provisioning should be done from the admin user management module.
          </p>
        </aside>

        <Card className="auth-card auth-reveal w-full max-w-[460px] justify-self-center space-y-4 !rounded-3xl !p-6 sm:!p-7 lg:justify-self-end">
          <div className="text-center">
            <div className="mx-auto mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-sky-600 text-white shadow-soft">
              <GraduationCap size={24} />
            </div>
            <p className="text-xs uppercase tracking-widest text-brand-500">CAPS AI</p>
            <h1 className="mt-1 text-2xl font-semibold">Bootstrap super admin</h1>
          </div>

          <form className="grid gap-3" onSubmit={onSubmit}>
            <FormInput label="Full Name" name="full_name" required value={form.full_name} onChange={onChange} />
            <FormInput label="Email" name="email" type="email" required value={form.email} onChange={onChange} />
            <FormInput label="Password" name="password" type="password" minLength={8} required value={form.password} onChange={onChange} />
            <FormInput label="Role" name="role" value="admin" readOnly disabled />
            <FormInput label="Admin Type" name="admin_type" value="super_admin" readOnly disabled />
            <p className="text-xs text-slate-500">
              Bootstrap-only route: this page works only when no admin exists. After bootstrap, users must be provisioned by admin from the users module.
            </p>

            <button className="btn-primary !bg-sky-600 hover:!bg-sky-700" type="submit" disabled={loading}>
              {loading ? 'Creating super admin...' : 'Create Super Admin'}
            </button>
          </form>

          {error ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p> : null}

          <p className="text-sm text-slate-600">
            Already registered? <Link className="font-medium text-brand-600" to="/login">Login here</Link>
          </p>
        </Card>
      </section>
    </main>
  );
}
