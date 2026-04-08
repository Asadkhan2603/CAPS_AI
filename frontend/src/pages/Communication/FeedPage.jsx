import { useEffect, useMemo, useState } from 'react';
import { RefreshCcw, Search } from 'lucide-react';
import CommunicationTabs from '../../components/communication/CommunicationTabs';
import FeedCard from '../../components/communication/FeedCard';
import { apiClient } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';

const PAGE_SIZE = 10;
const SOURCE_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'announcement', label: 'Announcements' },
  { key: 'notification', label: 'Notifications' },
  { key: 'assignment', label: 'Assignments' },
  { key: 'evaluation', label: 'Evaluations' }
];

function roleActorLabel(role) {
  if (role === 'admin') return 'Admin';
  if (role === 'teacher') return 'Teacher';
  return 'System';
}

function noticeDeliveryMeta(notice) {
  const scheduledAt = notice.scheduled_at ? new Date(notice.scheduled_at).getTime() : null;
  if (scheduledAt && scheduledAt > Date.now()) {
    return `Scheduled for ${new Date(notice.scheduled_at).toLocaleString()}`;
  }
  if (notice.fanout_status === 'failed') {
    return 'Delivery failed';
  }
  if (notice.fanout_status === 'dispatched') {
    return `Delivered to ${notice.fanout_count ?? 0} recipients`;
  }
  if (notice.fanout_status === 'queued') {
    return 'Delivery queued';
  }
  return '';
}

export default function FeedPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [query, setQuery] = useState('');

  async function loadFeed() {
    setLoading(true);
    setError('');
    try {
      const [noticesRes, notificationsRes, assignmentsRes, evaluationsRes] = await Promise.allSettled([
        apiClient.get('/notices/', { params: { include_expired: true, include_scheduled: user?.role !== 'student', skip: 0, limit: 60 } }),
        apiClient.get('/notifications/', { params: { skip: 0, limit: 60 } }),
        apiClient.get('/assignments/', { params: { skip: 0, limit: 60 } }),
        apiClient.get('/evaluations/', { params: { skip: 0, limit: 60 } })
      ]);

      const feedItems = [];

      if (noticesRes.status === 'fulfilled') {
        (noticesRes.value.data || []).forEach((notice) => {
          feedItems.push({
            id: `notice-${notice.id}`,
            type: 'announcement',
            actor: notice.created_by === user?.id ? 'You' : 'Institution',
            action: notice.priority === 'urgent' ? 'posted an urgent announcement' : 'posted an announcement',
            targetAudience: notice.scope === 'college' ? 'Audience: College-wide' : `Audience: ${notice.scope}`,
            meta: noticeDeliveryMeta(notice),
            context: 'Announcement',
            createdAt: notice.created_at,
            priority: notice.priority,
            isUnread: !notice.is_read,
            searchableText: `${notice.title || ''} ${notice.message || ''} ${notice.scope || ''}`.toLowerCase(),
            actionLink: { label: 'Open Announcement', to: `/communication/announcements?highlight=${encodeURIComponent(notice.id)}` }
          });
        });
      }

      if (notificationsRes.status === 'fulfilled') {
        (notificationsRes.value.data || []).forEach((notification) => {
          feedItems.push({
            id: `notification-${notification.id}`,
            type: 'notification',
            actor: notification.created_by === user?.id ? 'You' : (notification.created_by_label || 'System'),
            action: 'issued a system alert',
            targetAudience: `Scope: ${notification.scope || 'global'}`,
            meta: notification.target_user_id
              ? `Target: ${notification.target_user_label || notification.target_user_id}`
              : 'Target: Global',
            context: 'System',
            createdAt: notification.created_at,
            priority: notification.priority,
            isUnread: !notification.is_read,
            searchableText: `${notification.title || ''} ${notification.message || ''} ${notification.scope || ''}`.toLowerCase(),
            actionLink: { label: 'Open Notification', to: `/notifications?highlight=${encodeURIComponent(notification.id)}` }
          });
        });
      }

      if (assignmentsRes.status === 'fulfilled') {
        (assignmentsRes.value.data || []).forEach((assignment) => {
          feedItems.push({
            id: `assignment-${assignment.id}`,
            type: 'assignment',
            actor: assignment.created_by === user?.id ? 'You' : roleActorLabel(user?.role),
            action: 'created an assignment',
            targetAudience: assignment.class_label
              ? `Section: ${assignment.class_label}`
              : assignment.class_public_id
              ? `Section: ${assignment.class_public_id}`
              : 'Section: -',
            context: 'Assignment',
            createdAt: assignment.created_at,
            isUnread: false,
            searchableText: `${assignment.title || ''} ${assignment.description || ''} ${assignment.class_label || assignment.class_public_id || ''}`.toLowerCase(),
            actionLink: { label: 'Open Assignments', to: '/assignments' }
          });
        });
      }

      if (evaluationsRes.status === 'fulfilled') {
        (evaluationsRes.value.data || []).forEach((evaluation) => {
          feedItems.push({
            id: `evaluation-${evaluation.id}`,
            type: 'evaluation',
            actor: evaluation.teacher_user_id === user?.id ? 'You' : roleActorLabel(user?.role),
            action: evaluation.is_finalized ? 'published grades' : 'completed an evaluation',
            targetAudience: evaluation.student_label
              ? `Student: ${evaluation.student_label}`
              : evaluation.student_public_id
              ? `Student: ${evaluation.student_public_id}`
              : 'Student: -',
            context: 'Evaluation',
            createdAt: evaluation.created_at,
            isUnread: false,
            searchableText: `${evaluation.student_label || ''} ${evaluation.student_public_id || ''}`.toLowerCase(),
            actionLink: { label: 'Open Evaluations', to: '/evaluations' }
          });
        });
      }

      const sorted = feedItems
        .filter((item) => item.createdAt)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      setItems(sorted);
      setPage(1);
    } catch (err) {
      const message = formatApiError(err, 'Unable to load feed');
      setError(message);
      pushToast({ title: 'Feed load failed', description: message, variant: 'error' });
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFeed();
  }, []);

  const summary = useMemo(() => {
    const unread = items.filter((item) => item.isUnread).length;
    return {
      total: items.length,
      unread,
      announcements: items.filter((item) => item.type === 'announcement').length,
      notifications: items.filter((item) => item.type === 'notification').length
    };
  }, [items]);

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return items.filter((item) => {
      if (sourceFilter !== 'all' && item.type !== sourceFilter) return false;
      if (unreadOnly && !item.isUnread) return false;
      if (!normalizedQuery) return true;
      const haystack = `${item.actor} ${item.action} ${item.targetAudience} ${item.meta || ''} ${item.context} ${item.searchableText || ''}`.toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [items, query, sourceFilter, unreadOnly]);

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
  const pagedItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredItems.slice(start, start + PAGE_SIZE);
  }, [filteredItems, page]);

  useEffect(() => {
    setPage(1);
  }, [query, sourceFilter, unreadOnly]);

  return (
    <div className="page-fade">
      <div className="mx-auto max-w-5xl">
        <CommunicationTabs />

        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Activity Feed</h1>
            <p className="text-sm text-slate-500">Chronological stream of communication and academic events with direct routes back to the source module.</p>
          </div>
          <button className="btn-secondary" onClick={loadFeed} disabled={loading}>
            <RefreshCcw size={15} /> Refresh
          </button>
        </div>

        <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Loaded</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{summary.total}</p>
          </div>
          <div className="rounded-2xl border border-brand-200 bg-brand-50/50 px-4 py-3 dark:border-brand-800/60 dark:bg-brand-900/10">
            <p className="text-xs uppercase tracking-wide text-slate-500">Unread Signals</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{summary.unread}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Announcements</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{summary.announcements}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Notifications</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{summary.notifications}</p>
          </div>
        </div>

        <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center gap-2">
            {SOURCE_FILTERS.map((filter) => (
              <button
                key={filter.key}
                type="button"
                className={`rounded-xl border px-3 py-1.5 text-sm transition ${
                  sourceFilter === filter.key
                    ? 'border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}
                onClick={() => setSourceFilter(filter.key)}
              >
                {filter.label}
              </button>
            ))}
            <button
              type="button"
              className={`rounded-xl border px-3 py-1.5 text-sm transition ${
                unreadOnly
                  ? 'border-brand-600 bg-brand-600 text-white dark:border-brand-500 dark:bg-brand-500 dark:text-slate-950'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
              onClick={() => setUnreadOnly((value) => !value)}
            >
              Unread Only
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="relative min-w-[16rem] flex-1">
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                className="input pl-9"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search announcements, notifications, assignments, or evaluations"
              />
            </label>
            {(query || sourceFilter !== 'all' || unreadOnly) ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setQuery('');
                  setSourceFilter('all');
                  setUnreadOnly(false);
                }}
              >
                Reset Filters
              </button>
            ) : null}
          </div>
        </div>

        <div className="space-y-3">
          {loading ? <p className="text-sm text-slate-500">Loading feed...</p> : null}
          {error ? (
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm text-rose-600">{error}</p>
              <button className="btn-secondary" onClick={loadFeed}>
                Retry
              </button>
            </div>
          ) : null}
          {!loading && pagedItems.length === 0 ? (
            <p className="text-sm text-slate-500">
              {items.length === 0 ? 'No activity available.' : 'No activity matches the current filters.'}
            </p>
          ) : null}
          {pagedItems.map((item) => (
            <FeedCard key={item.id} item={item} />
          ))}
        </div>

        <div className="mt-4 flex items-center justify-end gap-2 text-sm">
          <button className="btn-secondary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
            Prev
          </button>
          <span className="text-slate-500">
            {page} / {totalPages}
          </span>
          <button
            className="btn-secondary"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
