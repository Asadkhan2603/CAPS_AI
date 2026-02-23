import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
    role: 'teacher',
    extended_roles: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function onExtendedRoleChange(event) {
    const { value, checked } = event.target;
    setForm((prev) => {
      const nextRoles = checked
        ? [...prev.extended_roles, value]
        : prev.extended_roles.filter((item) => item !== value);
      return { ...prev, extended_roles: nextRoles };
    });
  }

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const payload = {
        ...form,
        extended_roles: form.role === 'teacher' ? form.extended_roles : []
      };
      await register(payload);
      await login(form.email, form.password);
      pushToast({ title: 'Account ready', description: 'Registration completed.', variant: 'success' });
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
    <main className="grid min-h-screen place-items-center bg-gradient-to-br from-brand-50 via-slate-50 to-sky-100 p-4 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <Card className="w-full max-w-lg space-y-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-brand-500">CAPS AI</p>
          <h1 className="mt-1 text-2xl font-semibold">Create your account</h1>
        </div>

        <form className="grid gap-3" onSubmit={onSubmit}>
          <FormInput label="Full Name" name="full_name" required value={form.full_name} onChange={onChange} />
          <FormInput label="Email" name="email" type="email" required value={form.email} onChange={onChange} />
          <FormInput label="Password" name="password" type="password" minLength={8} required value={form.password} onChange={onChange} />
          <FormInput label="Role" as="select" name="role" value={form.role} onChange={onChange}>
            <option value="admin">Admin</option>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
          </FormInput>

          {form.role === 'teacher' ? (
            <div className="rounded-2xl border border-slate-200 p-3 dark:border-slate-700">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Teacher Extensions</p>
              <div className="space-y-1 text-sm">
                <label className="flex items-center gap-2"><input type="checkbox" value="year_head" checked={form.extended_roles.includes('year_head')} onChange={onExtendedRoleChange} /> Year Head</label>
                <label className="flex items-center gap-2"><input type="checkbox" value="class_coordinator" checked={form.extended_roles.includes('class_coordinator')} onChange={onExtendedRoleChange} /> Class Coordinator</label>
                <label className="flex items-center gap-2"><input type="checkbox" value="club_coordinator" checked={form.extended_roles.includes('club_coordinator')} onChange={onExtendedRoleChange} /> Club Coordinator</label>
              </div>
            </div>
          ) : null}

          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        {error ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600 dark:bg-rose-900/20 dark:text-rose-300">{error}</p> : null}

        <p className="text-sm text-slate-600 dark:text-slate-300">
          Already registered? <Link className="font-medium text-brand-600" to="/login">Login here</Link>
        </p>
      </Card>
    </main>
  );
}
