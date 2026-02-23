import { useEffect, useMemo, useState } from 'react';
import { RefreshCcw } from 'lucide-react';
import CommunicationTabs from '../../components/communication/CommunicationTabs';
import FeedCard from '../../components/communication/FeedCard';
import { apiClient } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';

const PAGE_SIZE = 10;

function roleActorLabel(role) {
  if (role === 'admin') return 'Admin';
  if (role === 'teacher') return 'Teacher';
  return 'System';
}

export default function FeedPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);

  async function loadFeed() {
    setLoading(true);
    try {
      const [noticesRes, notificationsRes, assignmentsRes, evaluationsRes] = await Promise.allSettled([
        apiClient.get('/notices/', { params: { include_expired: true, skip: 0, limit: 60 } }),
        apiClient.get('/notifications/', { params: { skip: 0, limit: 60 } }),
        apiClient.get('/assignments/', { params: { skip: 0, limit: 60 } }),
        apiClient.get('/evaluations/', { params: { skip: 0, limit: 60 } })
      ]);

      const feedItems = [];

      if (noticesRes.status === 'fulfilled') {
        (noticesRes.value.data || []).forEach((notice) => {
          feedItems.push({
            id: `notice-${notice.id}`,
            actor: notice.created_by === user?.id ? 'You' : roleActorLabel(user?.role),
            action: notice.priority === 'urgent' ? 'posted an urgent announcement' : 'posted an announcement',
            targetAudience: notice.scope === 'college' ? 'Audience: College-wide' : `Audience: ${notice.scope}`,
            context: 'Announcement',
            createdAt: notice.created_at,
            priority: notice.priority
          });
        });
      }

      if (notificationsRes.status === 'fulfilled') {
        (notificationsRes.value.data || []).forEach((notification) => {
          feedItems.push({
            id: `notification-${notification.id}`,
            actor: notification.created_by === user?.id ? 'You' : 'System',
            action: 'issued a system alert',
            targetAudience: `Scope: ${notification.scope || 'global'}`,
            context: 'System',
            createdAt: notification.created_at,
            priority: notification.priority
          });
        });
      }

      if (assignmentsRes.status === 'fulfilled') {
        (assignmentsRes.value.data || []).forEach((assignment) => {
          feedItems.push({
            id: `assignment-${assignment.id}`,
            actor: assignment.created_by === user?.id ? 'You' : roleActorLabel(user?.role),
            action: 'created an assignment',
            targetAudience: assignment.class_id ? `Class: ${assignment.class_id}` : 'Class: -',
            context: 'Assignment',
            createdAt: assignment.created_at
          });
        });
      }

      if (evaluationsRes.status === 'fulfilled') {
        (evaluationsRes.value.data || []).forEach((evaluation) => {
          feedItems.push({
            id: `evaluation-${evaluation.id}`,
            actor: evaluation.teacher_user_id === user?.id ? 'You' : roleActorLabel(user?.role),
            action: evaluation.is_finalized ? 'published grades' : 'completed an evaluation',
            targetAudience: evaluation.student_user_id ? `Student: ${evaluation.student_user_id}` : 'Student: -',
            context: 'Evaluation',
            createdAt: evaluation.created_at
          });
        });
      }

      const sorted = feedItems
        .filter((item) => item.createdAt)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      setItems(sorted);
      setPage(1);
    } catch (err) {
      pushToast({ title: 'Feed load failed', description: formatApiError(err, 'Unable to load feed'), variant: 'error' });
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFeed();
  }, []);

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const pagedItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return items.slice(start, start + PAGE_SIZE);
  }, [items, page]);

  return (
    <div className="page-fade">
      <div className="mx-auto max-w-5xl">
        <CommunicationTabs />

        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Activity Feed</h1>
            <p className="text-sm text-slate-500">Chronological stream of communication and academic events.</p>
          </div>
          <button className="btn-secondary" onClick={loadFeed} disabled={loading}>
            <RefreshCcw size={15} /> Refresh
          </button>
        </div>

        <div className="space-y-3">
          {loading ? <p className="text-sm text-slate-500">Loading feed...</p> : null}
          {!loading && pagedItems.length === 0 ? <p className="text-sm text-slate-500">No activity available.</p> : null}
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
