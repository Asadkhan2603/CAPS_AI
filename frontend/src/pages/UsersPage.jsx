import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { cn } from '../utils/cn';

const EXTENSIONS = ['year_head', 'class_coordinator', 'club_coordinator'];

function FlipButton({ checked, disabled, onClick, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-2 py-1 text-xs transition',
        checked
          ? 'border-brand-400 bg-brand-100 text-brand-700 dark:border-brand-600 dark:bg-brand-900/30 dark:text-brand-300'
          : 'border-slate-300 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300',
        disabled && 'cursor-not-allowed opacity-60'
      )}
    >
      <span
        className={cn(
          'relative h-5 w-9 rounded-full transition-colors',
          checked ? 'bg-brand-500' : 'bg-slate-300 dark:bg-slate-700'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform',
            checked ? 'left-4' : 'left-0.5'
          )}
        />
      </span>
      <span>{label}</span>
    </button>
  );
}

export default function UsersPage() {
  const { pushToast } = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [q, setQ] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [draftRoles, setDraftRoles] = useState({});
  const [savingIds, setSavingIds] = useState([]);

  async function loadUsers() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/users/');
      setRows(response.data);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to load users';
      setError(String(detail));
      pushToast({ title: 'Load failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  function getEffectiveExtensions(row) {
    return draftRoles[row.id] ?? row.extended_roles ?? [];
  }

  function toggleExtension(row, extension) {
    const current = getEffectiveExtensions(row);
    const next = current.includes(extension) ? current.filter((item) => item !== extension) : [...current, extension];
    setDraftRoles((prev) => ({ ...prev, [row.id]: next }));
  }

  async function saveExtensions(row) {
    const next = getEffectiveExtensions(row);
    setSavingIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    try {
      await apiClient.patch(`/users/${row.id}/extensions`, { extended_roles: next });
      setRows((prev) =>
        prev.map((item) => (item.id === row.id ? { ...item, extended_roles: next } : item))
      );
      setDraftRoles((prev) => {
        const copy = { ...prev };
        delete copy[row.id];
        return copy;
      });
      pushToast({ title: 'Updated', description: 'Extension roles updated.', variant: 'success' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update extension roles';
      pushToast({ title: 'Update failed', description: String(detail), variant: 'error' });
    } finally {
      setSavingIds((prev) => prev.filter((id) => id !== row.id));
    }
  }

  const filteredRows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter((row) => {
      const roleMatch = roleFilter ? row.role === roleFilter : true;
      if (!roleMatch) return false;
      if (!needle) return true;
      return (
        row.full_name?.toLowerCase().includes(needle) ||
        row.email?.toLowerCase().includes(needle)
      );
    });
  }, [q, roleFilter, rows]);

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'email', label: 'Email' },
      { key: 'role', label: 'Role' },
      {
        key: 'extended_roles',
        label: 'Extension Roles',
        render: (row) => {
          if (row.role !== 'teacher') return '-';
          const current = getEffectiveExtensions(row);
          const saving = savingIds.includes(row.id);
          return (
            <div className="flex flex-wrap items-center gap-2">
              {EXTENSIONS.map((extension) => (
                <FlipButton
                  key={extension}
                  checked={current.includes(extension)}
                  disabled={saving}
                  onClick={() => toggleExtension(row, extension)}
                  label={extension}
                />
              ))}
            </div>
          );
        }
      }
    ],
    [draftRoles, savingIds]
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Users</h1>
          <button className="btn-secondary" onClick={loadUsers}>Refresh</button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <FormInput label="Search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name / Email" />
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Role</span>
            <select className="input" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
              <option value="">All</option>
              <option value="admin">admin</option>
              <option value="teacher">teacher</option>
              <option value="student">student</option>
            </select>
          </label>
        </div>
      </Card>

      <Card className="space-y-3">
        {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <Table
          columns={columns}
          data={filteredRows}
          rowActions={[
            {
              key: 'save',
              label: 'Save',
              onClick: async (row) => {
                if (row.role !== 'teacher') return;
                await saveExtensions(row);
              }
            }
          ]}
        />
      </Card>
    </div>
  );
}

