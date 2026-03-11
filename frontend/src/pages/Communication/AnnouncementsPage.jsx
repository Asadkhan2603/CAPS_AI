import { useEffect, useMemo, useState } from 'react';
import { Plus, Search } from 'lucide-react';
import CommunicationTabs from '../../components/communication/CommunicationTabs';
import AnnouncementCard from '../../components/communication/AnnouncementCard';
import CreateAnnouncementModal from '../../components/communication/CreateAnnouncementModal';
import EmptyState from '../../components/ui/EmptyState';
import { apiClient } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { pushApiErrorToast } from '../../utils/errorToast';
import { isNoticeRead, markNoticeRead, markNoticesRead, unreadNoticeCount } from '../../utils/noticeReadTracker';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'urgent', label: 'Urgent' },
  { key: 'expiring', label: 'Expiring Soon' },
  { key: 'expired', label: 'Expired' },
  { key: 'mine', label: 'My Published' }
];

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [notices, setNotices] = useState([]);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [showCreate, setShowCreate] = useState(false);
  const [batches, setBatches] = useState([]);
  const [sections, setSections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [noticeReadVersion, setNoticeReadVersion] = useState(0);

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
          searchText: `${label} section class ${item.branch_name || ''}`.toLowerCase(),
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
  }, [activeFilter, notices, search, user?.id, noticeReadVersion]);

  const unreadCount = useMemo(() => unreadNoticeCount(user?.id, visibleNotices), [user?.id, visibleNotices, noticeReadVersion]);

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
      if (payload.scope_ref_id) {
        formData.append('scope_ref_id', payload.scope_ref_id);
      }
      if (payload.expires_at) {
        formData.append('expires_at', payload.expires_at);
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
      } else {
        pushToast({ title: 'Published', description: 'Announcement published successfully.', variant: 'success' });
      }
      setShowCreate(false);
      await loadNotices();
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to publish announcement');
    } finally {
      setPublishing(false);
      setUploadProgress(0);
    }
  }

  function handleMarkRead(noticeId) {
    markNoticeRead(user?.id, noticeId);
    setNoticeReadVersion((v) => v + 1);
  }

  function handleMarkAllRead() {
    markNoticesRead(user?.id, visibleNotices.map((item) => item.id));
    setNoticeReadVersion((v) => v + 1);
    pushToast({ title: 'Done', description: 'All visible announcements marked as read.', variant: 'success' });
  }

  return (
    <div className="page-fade">
      <div className="mx-auto max-w-5xl">
        <CommunicationTabs />

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
              <AnnouncementCard
                key={notice.id}
                notice={notice}
                audienceText={audienceText}
                isRead={isNoticeRead(user?.id, notice.id)}
                onMarkRead={handleMarkRead}
              />
            );
          })}
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
    </div>
  );
}
