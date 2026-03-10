import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';

const PRIORITY_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'info', label: 'Info' }
];

const SCOPE_OPTIONS = [
  { value: 'global', label: 'Global' },
  { value: 'notice', label: 'Notice' },
  { value: 'similarity', label: 'Similarity' },
  { value: 'ai', label: 'AI' },
  { value: 'system', label: 'System' }
];

function formatTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function priorityVariant(priority) {
  if (priority === 'urgent') return 'danger';
  if (priority === 'info') return 'info';
  return 'default';
}

export default function NotificationsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const canCreate = ['admin', 'teacher'].includes(user?.role || '');

  const [rows, setRows] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(20);
  const [filters, setFilters] = useState({
    is_read: '',
    scope: ''
  });
  const [form, setForm] = useState({
    title: '',
    message: '',
    priority: 'normal',
    scope: 'global',
    target_user_id: ''
  });

  async function loadNotifications(nextSkip = skip, nextLimit = limit, nextFilters = filters) {
    setLoading(true);
    setError('');
    try {
      const params = {
        skip: nextSkip,
        limit: nextLimit
      };
      if (nextFilters.is_read !== '') {
        params.is_read = nextFilters.is_read === 'true';
      }
      if (nextFilters.scope) {
        params.scope = nextFilters.scope;
      }

      const response = await apiClient.get('/notifications/', { params });
      setRows(response.data || []);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load notifications');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  async function loadUsers() {
    if (!canCreate) return;
    try {
      const response = await apiClient.get('/users/');
      setUsers(response.data || []);
    } catch {
      setUsers([]);
    }
  }

  useEffect(() => {
    loadNotifications(skip, limit, filters);
  }, [skip, limit]);

  useEffect(() => {
    loadUsers();
  }, [canCreate]);

  const scopeOptions = useMemo(() => {
    const discovered = Array.from(new Set(rows.map((item) => item.scope).filter(Boolean)));
    const base = [...SCOPE_OPTIONS];
    discovered.forEach((scope) => {
      if (!base.some((item) => item.value === scope)) {
        base.push({ value: scope, label: scope });
      }
    });
    return base;
  }, [rows]);

  const userOptions = useMemo(
    () =>
      users
        .filter((item) => item.is_active !== false)
        .map((item) => ({
          value: item.id,
          label: `${item.full_name} (${item.email})`
        })),
    [users]
  );

  const userLabelById = useMemo(
    () => Object.fromEntries(userOptions.map((item) => [item.value, item.label])),
    [userOptions]
  );

  const stats = useMemo(() => {
    const unread = rows.filter((item) => !item.is_read).length;
    const urgent = rows.filter((item) => item.priority === 'urgent').length;
    return {
      total: rows.length,
      unread,
      urgent
    };
  }, [rows]);

  async function onApplyFilters(event) {
    event.preventDefault();
    setSkip(0);
    await loadNotifications(0, limit, filters);
  }

  async function onMarkRead(notificationId) {
    try {
      await apiClient.patch(`/notifications/${notificationId}/read`);
      setRows((prev) =>
        prev.map((item) => (item.id === notificationId ? { ...item, is_read: true } : item))
      );
      pushToast({ title: 'Marked as read', description: 'Notification state updated.', variant: 'success' });
    } catch (err) {
      pushToast({
        title: 'Update failed',
        description: formatApiError(err, 'Failed to mark notification as read'),
        variant: 'error'
      });
    }
  }

  async function onCreateNotification(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.post('/notifications/', {
        ...form,
        target_user_id: form.target_user_id || null
      });
      setForm({
        title: '',
        message: '',
        priority: 'normal',
        scope: 'global',
        target_user_id: ''
      });
      pushToast({ title: 'Created', description: 'Notification created successfully.', variant: 'success' });
      await loadNotifications(0, limit, filters);
      setSkip(0);
    } catch (err) {
      pushToast({
        title: 'Create failed',
        description: formatApiError(err, 'Failed to create notification'),
        variant: 'error'
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-2">
        <h1 className="text-2xl font-semibold">Notifications</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Review unread alerts, filter by scope, and acknowledge notifications directly.
        </p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="!p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Loaded</p>
          <p className="mt-1 text-3xl font-bold">{stats.total}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Unread</p>
          <p className="mt-1 text-3xl font-bold">{stats.unread}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Urgent</p>
          <p className="mt-1 text-3xl font-bold">{stats.urgent}</p>
        </Card>
      </div>

      <Card>
        <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={onApplyFilters}>
          <FormInput
            as="select"
            label="Read State"
            value={filters.is_read}
            onChange={(event) => setFilters((prev) => ({ ...prev, is_read: event.target.value }))}
          >
            <option value="">All</option>
            <option value="false">Unread</option>
            <option value="true">Read</option>
          </FormInput>
          <FormInput
            as="select"
            label="Scope"
            value={filters.scope}
            onChange={(event) => setFilters((prev) => ({ ...prev, scope: event.target.value }))}
          >
            <option value="">All Scopes</option>
            {scopeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </FormInput>
          <div className="flex items-end gap-2">
            <button type="submit" className="btn-primary w-full">
              Apply
            </button>
            <button
              type="button"
              className="btn-secondary w-full"
              onClick={() => {
                const nextFilters = { is_read: '', scope: '' };
                setFilters(nextFilters);
                setSkip(0);
                loadNotifications(0, limit, nextFilters);
              }}
            >
              Reset
            </button>
          </div>
        </form>
      </Card>

      {canCreate ? (
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Create Notification</h2>
          <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={onCreateNotification}>
            <FormInput
              label="Title"
              required
              value={form.title}
              onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
            />
            <FormInput
              as="select"
              label="Priority"
              value={form.priority}
              onChange={(event) => setForm((prev) => ({ ...prev, priority: event.target.value }))}
            >
              {PRIORITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FormInput>
            <FormInput
              as="select"
              label="Scope"
              value={form.scope}
              onChange={(event) => setForm((prev) => ({ ...prev, scope: event.target.value }))}
            >
              {scopeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FormInput>
            <FormInput
              as="textarea"
              className="sm:col-span-2 xl:col-span-2"
              label="Message"
              required
              value={form.message}
              onChange={(event) => setForm((prev) => ({ ...prev, message: event.target.value }))}
            />
            <FormInput
              as="select"
              label="Target User"
              value={form.target_user_id}
              onChange={(event) => setForm((prev) => ({ ...prev, target_user_id: event.target.value }))}
            >
              <option value="">Global Notification</option>
              {userOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FormInput>
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create'}
              </button>
            </div>
          </form>
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Notification Center</h2>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>
              Prev
            </button>
            <span className="text-xs text-slate-500">skip: {skip}</span>
            <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>
              Next
            </button>
            <select className="input w-24" value={limit} onChange={(event) => setLimit(Number(event.target.value))}>
              {[10, 20, 50].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? <p className="text-sm text-slate-500">Loading notifications...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <div className="space-y-3">
          {rows.length === 0 && !loading ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-300">
              No notifications found for the current filters.
            </div>
          ) : null}

          {rows.map((item) => (
            <div
              key={item.id}
              className={`rounded-2xl border p-4 ${
                item.is_read
                  ? 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
                  : 'border-brand-200 bg-brand-50/40 dark:border-brand-700/60 dark:bg-brand-900/10'
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{item.title}</h3>
                    <Badge variant={priorityVariant(item.priority)}>{item.priority || 'normal'}</Badge>
                    <Badge variant={item.is_read ? 'default' : 'info'}>{item.is_read ? 'Read' : 'Unread'}</Badge>
                    <Badge>{item.scope || 'general'}</Badge>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-200">{item.message}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Created {formatTimestamp(item.created_at)}
                    {item.target_user_id ? ` | Target: ${userLabelById[item.target_user_id] || item.target_user_id}` : ' | Target: Global'}
                  </p>
                </div>
                {!item.is_read ? (
                  <button className="btn-secondary" onClick={() => onMarkRead(item.id)}>
                    Mark Read
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
