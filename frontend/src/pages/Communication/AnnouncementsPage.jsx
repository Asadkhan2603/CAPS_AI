import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSearchParams } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import CommunicationTabs from '../../components/communication/CommunicationTabs';
import AnnouncementCard from '../../components/communication/AnnouncementCard';
import CommunicationDeliveryModal from '../../components/communication/CommunicationDeliveryModal';
import CreateAnnouncementModal from '../../components/communication/CreateAnnouncementModal';
import EmptyState from '../../components/ui/EmptyState';
import { apiClient } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { formatApiError } from '../../utils/apiError';
import { pushApiErrorToast } from '../../utils/errorToast';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'urgent', label: 'Urgent' },
  { key: 'expiring', label: 'Expiring Soon' },
  { key: 'expired', label: 'Expired' },
  { key: 'mine', label: 'My Published' }
];

function notifyNoticeBadgeRefresh() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('caps-ai:notices-changed'));
  }
}

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [notices, setNotices] = useState([]);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [showCreate, setShowCreate] = useState(false);
  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const [deliveryLoading, setDeliveryLoading] = useState(false);
  const [deliveryError, setDeliveryError] = useState('');
  const [deliveryNoticeId, setDeliveryNoticeId] = useState('');
  const [deliveryDetails, setDeliveryDetails] = useState(null);
  const [retryingDeliveryTarget, setRetryingDeliveryTarget] = useState('');
  const [batches, setBatches] = useState([]);
  const [sections, setSections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const highlightedNoticeId = searchParams.get('highlight') || '';

  const canCreate = user?.role === 'admin' || user?.role === 'teacher';
  const isStudent = user?.role === 'student';
  const visibleFilters = useMemo(
    () => FILTERS.filter((item) => !(isStudent && item.key === 'mine')),
    [isStudent]
  );

  async function loadLookups() {
    const [batchesRes, sectionsRes, subjectsRes] = await Promise.allSettled([
      apiClient.get('/batches/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/sections/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/subjects/', { params: { skip: 0, limit: 100 } })
    ]);

    setBatches(batchesRes.status === 'fulfilled' ? batchesRes.value.data || [] : []);
    setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value.data || [] : []);
    setSubjects(subjectsRes.status === 'fulfilled' ? subjectsRes.value.data || [] : []);
  }

  async function loadNotices() {
    setLoading(true);
    try {
      const response = await apiClient.get('/notices/', {
        params: {
          include_expired: true,
          include_scheduled: canCreate,
          priority: activeFilter === 'urgent' ? 'urgent' : undefined,
          skip: 0,
          limit: 100
        }
      });
      const rows = (response.data || []).sort(
        (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
      );
      setNotices(rows);
      setPage(1);
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to load announcements');
      setNotices([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLookups();
  }, []);

  useEffect(() => {
    loadNotices();
  }, [activeFilter]);

  useEffect(() => {
    if (isStudent && activeFilter === 'mine') {
      setActiveFilter('all');
    }
  }, [isStudent, activeFilter]);

  useEffect(() => {
    if (!highlightedNoticeId || loading || notices.length === 0) return;
    const timer = window.setTimeout(() => {
      const target = document.getElementById(`announcement-card-${highlightedNoticeId}`);
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [highlightedNoticeId, loading, notices.length]);

  const audienceNameById = useMemo(() => {
    const map = {};
    batches.forEach((item) => {
      map[item.id] = item.name || item.academic_span_label || item.code || 'Batch';
    });
    sections.forEach((item) => {
      map[item.id] = `${item.name}${item.faculty_name ? ` (${item.faculty_name})` : ''}`;
    });
    subjects.forEach((item) => {
      map[item.id] = `${item.name}${item.code ? ` (${item.code})` : ''}`;
    });
    return map;
  }, [batches, sections, subjects]);

  const audienceOptions = useMemo(() => {
    const options = [];
    const seen = new Set();
    const role = user?.role;
    const extensions = user?.extended_roles || [];

    if (role === 'admin') {
      const item = {
        key: 'college:all',
        label: 'Entire college',
        searchText: 'entire college college-wide all college'.toLowerCase(),
        scope: 'college',
        scopeRefId: null
      };
      seen.add(item.key);
      options.push(item);
    }

    const allowBatch = role === 'admin' || (role === 'teacher' && extensions.includes('year_head'));
    const allowClass = role === 'admin' || (role === 'teacher' && extensions.includes('class_coordinator'));
    const allowSubject = role === 'admin' || role === 'teacher';

    if (allowBatch) {
      batches.forEach((item) => {
        const label = item.name || item.academic_span_label || item.code || 'Batch';
        const option = {
          key: `batch:${item.id}`,
          label,
          searchText: `${label} batch ${item.code || ''}`.toLowerCase(),
          scope: 'batch',
          scopeRefId: item.id
        };
        if (!seen.has(option.key)) {
          seen.add(option.key);
          options.push(option);
        }
      });
    }

    if (allowClass) {
      sections.forEach((item) => {
        const label = `${item.name}${item.faculty_name ? ` (${item.faculty_name})` : ''}`;
        const option = {
          key: `class:${item.id}`,
          label,
          searchText: `${label} section class`.toLowerCase(),
          scope: 'section',
          scopeRefId: item.id
        };
        if (!seen.has(option.key)) {
          seen.add(option.key);
          options.push(option);
        }
      });
    }

    if (allowSubject) {
      subjects.forEach((item) => {
        const label = `${item.name}${item.code ? ` (${item.code})` : ''}`;
        const option = {
          key: `subject:${item.id}`,
          label,
          searchText: `${label} subject ${item.code || ''}`.toLowerCase(),
          scope: 'subject',
          scopeRefId: item.id
        };
        if (!seen.has(option.key)) {
          seen.add(option.key);
          options.push(option);
        }
      });
    }

    return options.sort((a, b) => a.label.localeCompare(b.label));
  }, [batches, sections, subjects, user?.extended_roles, user?.role]);

  const visibleNotices = useMemo(() => {
    const now = Date.now();
    const q = search.trim().toLowerCase();

    const filtered = notices.filter((notice) => {
      const expiryTs = notice.expires_at ? new Date(notice.expires_at).getTime() : null;
      const isExpired = expiryTs !== null && expiryTs <= now;
      const isExpiringSoon = expiryTs !== null && expiryTs > now && expiryTs <= now + 72 * 60 * 60 * 1000;

      if (activeFilter === 'expiring' && !isExpiringSoon) return false;
      if (activeFilter === 'expired' && !isExpired) return false;
      if (activeFilter === 'mine' && notice.created_by !== user?.id) return false;
      if (activeFilter === 'urgent' && notice.priority !== 'urgent') return false;

      if (!q) return true;
      const haystack = `${notice.title || ''} ${notice.message || ''}`.toLowerCase();
      return haystack.includes(q);
    });

    return filtered;
  }, [activeFilter, notices, search, user?.id]);

  const unreadCount = useMemo(
    () => visibleNotices.filter((item) => item?.id && !item?.is_read).length,
    [visibleNotices]
  );

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return visibleNotices.slice(start, start + pageSize);
  }, [page, pageSize, visibleNotices]);

  const totalPages = Math.max(1, Math.ceil(visibleNotices.length / pageSize));

  async function handlePublish(payload) {
    setPublishing(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append('title', payload.title);
      formData.append('message', payload.message);
      formData.append('priority', payload.priority);
      formData.append('scope', payload.scope);
      formData.append('is_pinned', String(Boolean(payload.is_pinned)));
      if (payload.template_key) {
        formData.append('template_key', payload.template_key);
      }
      if (payload.scope_ref_id) {
        formData.append('scope_ref_id', payload.scope_ref_id);
      }
      if (payload.expires_at) {
        formData.append('expires_at', payload.expires_at);
      }
      if (payload.scheduled_at) {
        formData.append('scheduled_at', payload.scheduled_at);
      }
      (payload.attachments || []).forEach((file) => formData.append('images', file));

      const response = await apiClient.post('/notices/', formData, {
        onUploadProgress: (event) => {
          const percent = event.total ? Math.round((event.loaded * 100) / event.total) : 0;
          setUploadProgress(percent);
        }
      });
      const savedImages = Array.isArray(response?.data?.images) ? response.data.images.length : 0;
      if ((payload.attachments || []).length > 0 && savedImages === 0) {
        pushToast({
          title: 'Published without image',
          description: 'Announcement was created but attachment upload failed. Check Cloudinary config and retry.',
          variant: 'warning'
        });
      } else if (payload.scheduled_at) {
        pushToast({
          title: 'Scheduled',
          description: 'Announcement saved and queued for future delivery.',
          variant: 'success'
        });
      } else {
        pushToast({ title: 'Published', description: 'Announcement published and delivery fanout is queued.', variant: 'success' });
      }
      setShowCreate(false);
      await loadNotices();
      notifyNoticeBadgeRefresh();
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to publish announcement');
    } finally {
      setPublishing(false);
      setUploadProgress(0);
    }
  }

  async function handleMarkRead(noticeId) {
    if (!noticeId) return;
    try {
      const response = await apiClient.post(`/notices/${noticeId}/read`);
      const updatedNotice = response.data;
      setNotices((current) => current.map((item) => (item.id === noticeId ? updatedNotice : item)));
      notifyNoticeBadgeRefresh();
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to mark announcement as read');
    }
  }

  async function handleMarkAllRead() {
    const unreadIds = visibleNotices.filter((item) => !item?.is_read).map((item) => item.id);
    if (unreadIds.length === 0) {
      pushToast({ title: 'Up to date', description: 'All visible announcements are already read.', variant: 'info' });
      return;
    }
    try {
      const response = await apiClient.post('/notices/read', { notice_ids: unreadIds });
      const updatedItems = Array.isArray(response.data?.items) ? response.data.items : [];
      const updatedById = new Map(updatedItems.map((item) => [item.id, item]));
      setNotices((current) => current.map((item) => updatedById.get(item.id) || item));
      notifyNoticeBadgeRefresh();
      pushToast({ title: 'Done', description: 'All visible announcements marked as read.', variant: 'success' });
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to mark announcements as read');
    }
  }

  async function loadDeliveryDetails(noticeId, { openModal = false } = {}) {
    if (!noticeId) return;
    if (openModal) {
      setDeliveryOpen(true);
      setDeliveryDetails(null);
      setDeliveryError('');
    }
    setDeliveryNoticeId(noticeId);
    setDeliveryLoading(true);
    try {
      const response = await apiClient.get(`/admin/communication/delivery/notices/${noticeId}`);
      setDeliveryDetails(response.data || null);
      setDeliveryError('');
    } catch (err) {
      setDeliveryDetails(null);
      setDeliveryError(formatApiError(err, 'Unable to load delivery details.'));
      pushApiErrorToast(pushToast, err, 'Unable to load delivery details');
    } finally {
      setDeliveryLoading(false);
    }
  }

  async function retryDeliveryEmail(target = null) {
    if (!deliveryNoticeId) return;
    const payload = target
      ? {
          target_user_ids: target.target_user_id ? [target.target_user_id] : [],
          target_emails: !target.target_user_id && target.target_email ? [target.target_email] : [],
          include_skipped: true
        }
      : { include_skipped: true };
    const retryKey = target ? `${target.target_user_id || ''}::${target.target_email || ''}` : '*';
    setRetryingDeliveryTarget(retryKey);
    try {
      const response = await apiClient.post(`/admin/communication/delivery/notices/${deliveryNoticeId}/retry-email`, payload);
      const retriedCount = Number(response.data?.retried_count || 0);
      setDeliveryDetails(response.data?.details || null);
      await loadNotices();
      pushToast({
        title: retriedCount > 0 ? 'Email retry queued' : 'Nothing to retry',
        description:
          retriedCount > 0
            ? `${retriedCount} recipient${retriedCount === 1 ? '' : 's'} reprocessed for email delivery.`
            : 'No failed or skipped email rows matched this retry action.',
        variant: retriedCount > 0 ? 'success' : 'info'
      });
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to retry email delivery');
    } finally {
      setRetryingDeliveryTarget('');
    }
  }

  return (
    <div className="page-fade">
      <div className="mx-auto max-w-5xl">
        <CommunicationTabs />

        <div className="mb-4 flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900 dark:border-sky-900/50 dark:bg-sky-950/30 dark:text-sky-100">
          <div>
            <p className="font-semibold">Announcements publish institutional updates. Club-specific posts stay in the clubs workspace.</p>
            <p className="mt-1 text-sky-800/90 dark:text-sky-200/85">
              Use this page for college, batch, section, and subject broadcasts. Use the Club Updates tab or jump straight to the club announcement workspace when you need club-owned communication.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link to="/clubs?tab=announcements" className="btn-secondary whitespace-nowrap">
              Open Club Updates
            </Link>
            <Link to="/clubs" className="btn-secondary whitespace-nowrap">
              Open Clubs Workspace
            </Link>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {visibleFilters.map((item) => (
              <button
                key={item.key}
                className={`rounded-xl border px-3 py-1.5 text-sm transition ${
                  activeFilter === item.key
                    ? 'border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}
                onClick={() => setActiveFilter(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <label className="relative w-64">
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                className="input pl-9"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search announcements"
              />
            </label>
            {canCreate ? (
              <button className="btn-primary" onClick={() => setShowCreate(true)}>
                <Plus size={15} /> New Announcement
              </button>
            ) : null}
            <button className="btn-secondary" onClick={handleMarkAllRead} disabled={visibleNotices.length === 0}>
              Mark All Read ({unreadCount})
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {loading ? <p className="text-sm text-slate-500">Loading announcements...</p> : null}
          {!loading && paged.length === 0 ? (
            <EmptyState title="No announcements found" description="Try another filter or create a new announcement." />
          ) : null}

          {paged.map((notice) => {
            const audienceText = notice.scope === 'college' ? 'Entire college' : audienceNameById[notice.scope_ref_id] || 'Targeted audience';
            return (
              <div key={notice.id} id={`announcement-card-${notice.id}`}>
                <AnnouncementCard
                  notice={notice}
                  audienceText={audienceText}
                  isRead={Boolean(notice?.is_read)}
                  onMarkRead={handleMarkRead}
                  canInspectDelivery={canCreate}
                  onViewDelivery={(item) => loadDeliveryDetails(item.id, { openModal: true })}
                  highlighted={highlightedNoticeId === notice.id}
                />
              </div>
            );
          })}
        </div>

        <div className="mt-4 flex items-center justify-end gap-2 text-sm">
          <button className="btn-secondary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
            Prev
          </button>
          {highlightedNoticeId ? (
            <button
              className="btn-secondary"
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.delete('highlight');
                setSearchParams(next, { replace: true });
              }}
            >
              Clear Highlight
            </button>
          ) : null}
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
          <select className="input w-20" value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            {[10, 20, 30].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      </div>

      <CreateAnnouncementModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onPublish={handlePublish}
        audienceOptions={audienceOptions}
        submitting={publishing}
        uploadProgress={uploadProgress}
      />
      <CommunicationDeliveryModal
        open={deliveryOpen}
        onClose={() => {
          setDeliveryOpen(false);
          setDeliveryError('');
          setRetryingDeliveryTarget('');
        }}
        onRefresh={() => loadDeliveryDetails(deliveryNoticeId)}
        onRetryAllEmail={() => retryDeliveryEmail()}
        onRetryRecipientEmail={(item) => retryDeliveryEmail(item)}
        loading={deliveryLoading}
        retryingTarget={retryingDeliveryTarget}
        error={deliveryError}
        details={deliveryDetails}
        title="Announcement Delivery"
      />
    </div>
  );
}
