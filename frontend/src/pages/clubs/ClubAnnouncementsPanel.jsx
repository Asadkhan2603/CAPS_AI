import { useEffect, useMemo, useState } from 'react';
import { Megaphone, Pin, RefreshCcw, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import AnnouncementCard from '../../components/communication/AnnouncementCard';
import CreateAnnouncementModal from '../../components/communication/CreateAnnouncementModal';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import { useToast } from '../../hooks/useToast';
import { apiClient } from '../../services/apiClient';
import { pushApiErrorToast } from '../../utils/errorToast';

const announcementTemplates = [
  {
    key: 'club_update',
    label: 'Club Update',
    title: 'Weekly Club Update',
    message: 'Share a short progress update, highlights from the last week, and the next action members should take.',
    priority: 'normal',
    is_pinned: false,
  },
  {
    key: 'event_reminder',
    label: 'Event Reminder',
    title: 'Upcoming Event Reminder',
    message: 'Remind members about the event date, check-in time, venue, and what they should carry.',
    priority: 'urgent',
    is_pinned: true,
  },
  {
    key: 'recruitment_campaign',
    label: 'Recruitment Push',
    title: 'Recruitment Window Open',
    message: 'Tell students why this club matters right now, how to join, and who should reach out for questions.',
    priority: 'normal',
    is_pinned: true,
  },
  {
    key: 'celebration',
    label: 'Celebration',
    title: 'Club Achievement Spotlight',
    message: 'Celebrate a win, thank the members involved, and let the community know what this milestone means.',
    priority: 'normal',
    is_pinned: false,
  },
];

function notifyNoticeBadgeRefresh() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('caps-ai:notices-changed'));
  }
}

function getTemplateByKey(templateKey) {
  return announcementTemplates.find((item) => item.key === templateKey) || null;
}

export default function ClubAnnouncementsPanel({ selectedClub, canPublish = false }) {
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [notices, setNotices] = useState([]);
  const [announcementFilter, setAnnouncementFilter] = useState('all');
  const [announcementDraft, setAnnouncementDraft] = useState(null);
  const canModerate = Boolean(canPublish);

  const audienceOptions = useMemo(() => {
    if (!selectedClub) return [];
    return [
      {
        key: `club:${selectedClub.id}`,
        label: selectedClub.name,
        searchText: `${selectedClub.name} club ${selectedClub.category || ''}`.toLowerCase(),
        scope: 'club',
        scopeRefId: selectedClub.id,
      },
    ];
  }, [selectedClub]);

  const sortedNotices = useMemo(
    () =>
      [...notices].sort((a, b) => {
        const pinDelta = Number(Boolean(b?.is_pinned)) - Number(Boolean(a?.is_pinned));
        if (pinDelta !== 0) return pinDelta;
        return new Date(b?.created_at || 0).getTime() - new Date(a?.created_at || 0).getTime();
      }),
    [notices],
  );

  const filteredNotices = useMemo(() => {
    if (announcementFilter === 'unread') {
      return sortedNotices.filter((item) => !item?.is_read);
    }
    if (announcementFilter === 'pinned') {
      return sortedNotices.filter((item) => item?.is_pinned);
    }
    return sortedNotices;
  }, [announcementFilter, sortedNotices]);

  const unreadIds = useMemo(
    () => filteredNotices.filter((item) => !item?.is_read).map((item) => item.id).filter(Boolean),
    [filteredNotices],
  );

  async function loadNotices() {
    if (!selectedClub?.id) {
      setNotices([]);
      return;
    }
    setLoading(true);
    try {
      const response = await apiClient.get('/notices/', {
        params: {
          scope: 'club',
          scope_ref_id: selectedClub.id,
          include_expired: true,
          skip: 0,
          limit: 100,
        },
      });
      setNotices(response.data || []);
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to load club announcements');
      setNotices([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotices();
  }, [selectedClub?.id]);

  async function handlePublish(payload) {
    setPublishing(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append('title', payload.title);
      formData.append('message', payload.message);
      formData.append('priority', payload.priority);
      formData.append('scope', 'club');
      formData.append('scope_ref_id', selectedClub.id);
      formData.append('is_pinned', String(Boolean(payload.is_pinned)));
      if (payload.template_key) {
        formData.append('template_key', payload.template_key);
      }
      if (payload.expires_at) {
        formData.append('expires_at', payload.expires_at);
      }
      (payload.attachments || []).forEach((file) => formData.append('images', file));

      await apiClient.post('/notices/', formData, {
        onUploadProgress: (event) => {
          const percent = event.total ? Math.round((event.loaded * 100) / event.total) : 0;
          setUploadProgress(percent);
        },
      });
      setShowCreate(false);
      setAnnouncementDraft(null);
      pushToast({
        title: 'Announcement published',
        description: `Club announcement published for ${selectedClub.name}.`,
        variant: 'success',
      });
      notifyNoticeBadgeRefresh();
      await loadNotices();
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to publish club announcement');
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
      pushApiErrorToast(pushToast, err, 'Unable to mark club announcement as read');
    }
  }

  async function handleMarkVisibleRead() {
    if (!unreadIds.length) return;
    try {
      const response = await apiClient.post('/notices/read', { notice_ids: unreadIds });
      const updatedItems = response.data?.items || [];
      const updatedById = new Map(updatedItems.map((item) => [item.id, item]));
      setNotices((current) => current.map((item) => updatedById.get(item.id) || item));
      notifyNoticeBadgeRefresh();
      pushToast({
        title: 'Announcements updated',
        description: `${updatedItems.length} visible announcement${updatedItems.length === 1 ? '' : 's'} marked as read.`,
        variant: 'success',
      });
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to mark visible club announcements as read');
    }
  }

  async function handleTogglePinned(notice) {
    if (!notice?.id) return;
    try {
      const response = await apiClient.patch(`/notices/${notice.id}`, {
        is_pinned: !Boolean(notice.is_pinned),
      });
      const updated = response.data;
      setNotices((current) => current.map((item) => (item.id === notice.id ? updated : item)));
      pushToast({
        title: updated.is_pinned ? 'Announcement pinned' : 'Announcement unpinned',
        description: `${updated.title} has been ${updated.is_pinned ? 'pinned to the top' : 'returned to normal order'}.`,
        variant: 'success',
      });
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to update announcement pin state');
    }
  }

  async function handleArchive(notice) {
    if (!notice?.id) return;
    const confirmed = typeof window === 'undefined' ? true : window.confirm(`Archive "${notice.title}"?`);
    if (!confirmed) return;
    try {
      await apiClient.delete(`/notices/${notice.id}`);
      setNotices((current) => current.filter((item) => item.id !== notice.id));
      notifyNoticeBadgeRefresh();
      pushToast({
        title: 'Announcement archived',
        description: `${notice.title} has been removed from the active club feed.`,
        variant: 'success',
      });
    } catch (err) {
      pushApiErrorToast(pushToast, err, 'Unable to archive club announcement');
    }
  }

  function openTemplateDraft(templateKey) {
    const template = getTemplateByKey(templateKey);
    if (!template) return;
    setAnnouncementDraft({
      title: template.title,
      message: template.message,
      priority: template.priority,
      is_pinned: template.is_pinned,
      template_key: template.key,
    });
    setShowCreate(true);
  }

  if (!selectedClub) {
    return (
      <Card>
        <EmptyState
          title="Select a club first"
          description="Choose a club to view or publish club-scoped announcements."
        />
      </Card>
    );
  }

  return (
    <>
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Club Announcements</h2>
            <p className="text-sm text-slate-500">
              Publish, pin, review, and moderate updates scoped only to {selectedClub.name}.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="btn-secondary" onClick={loadNotices} disabled={loading}>
              <RefreshCcw size={15} /> Refresh
            </button>
            {unreadIds.length ? (
              <button className="btn-secondary" onClick={handleMarkVisibleRead}>
                Mark Visible Read
              </button>
            ) : null}
            {canPublish ? (
              <button
                className="btn-primary"
                onClick={() => {
                  setAnnouncementDraft(null);
                  setShowCreate(true);
                }}
              >
                <Megaphone size={15} /> New Club Announcement
              </button>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/25 dark:text-emerald-100">
          <div>
            <p className="font-semibold">Club announcements stay scoped to this club workspace.</p>
            <p className="mt-1 text-emerald-800/90 dark:text-emerald-200/85">
              Use this panel for member-facing club updates. For college, batch, section, or subject-wide broadcasts, switch back to central announcements in the communication shell.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link to="/communication/announcements" className="btn-secondary whitespace-nowrap">
              Open Central Announcements
            </Link>
            <Link to="/notifications" className="btn-secondary whitespace-nowrap">
              Open Notifications
            </Link>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Active Feed</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{sortedNotices.length}</p>
            <p className="mt-1 text-xs text-slate-500">Pinned notices stay first, then the newest communication.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Unread In View</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{unreadIds.length}</p>
            <p className="mt-1 text-xs text-slate-500">Use filters to isolate pinned posts or unread communication.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/60">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Templates Ready</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{announcementTemplates.length}</p>
            <p className="mt-1 text-xs text-slate-500">Start recruitment, reminders, celebration, and weekly updates faster.</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            { key: 'all', label: 'All' },
            { key: 'unread', label: 'Unread' },
            { key: 'pinned', label: 'Pinned' },
          ].map((filter) => (
            <button
              key={filter.key}
              type="button"
              className={`rounded-full border px-3 py-1.5 text-sm font-medium ${
                announcementFilter === filter.key
                  ? 'border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-900'
                  : 'border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900/60'
              }`}
              onClick={() => setAnnouncementFilter(filter.key)}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {canPublish ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Announcement Templates</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Use a starting point, then tailor the message before publishing it to the club.
                </p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm dark:bg-slate-950/60 dark:text-slate-300">
                Templates save time, but the final copy is still editable.
              </span>
            </div>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {announcementTemplates.map((template) => (
                <button
                  key={template.key}
                  type="button"
                  className="rounded-2xl border border-slate-200 bg-white p-4 text-left transition hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950/70 dark:hover:bg-slate-900/70"
                  onClick={() => openTemplateDraft(template.key)}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-slate-900 dark:text-slate-100">{template.label}</p>
                    {template.is_pinned ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-900/35 dark:text-amber-300">
                        Pinned by default
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{template.message}</p>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {loading ? <p className="text-sm text-slate-500">Loading club announcements...</p> : null}
        {!loading && filteredNotices.length === 0 ? (
          <EmptyState
            title="No club announcements in this view"
            description={
              canPublish
                ? 'Try another filter or publish a template-backed announcement to start the club feed.'
                : 'Club announcements will appear here once a coordinator or president publishes one.'
            }
          />
        ) : null}

        <div className="space-y-4">
          {filteredNotices.map((notice) => (
            <div key={notice.id} className="space-y-2">
              <AnnouncementCard
                notice={notice}
                audienceText={selectedClub.name}
                isRead={Boolean(notice?.is_read)}
                onMarkRead={handleMarkRead}
              />
              {canModerate ? (
                <div className="flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleTogglePinned(notice)}
                  >
                    <Pin size={14} /> {notice.is_pinned ? 'Unpin' : 'Pin to Top'}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary !border-rose-200 !text-rose-700 hover:!bg-rose-50 dark:!border-rose-900/50 dark:!text-rose-300 dark:hover:!bg-rose-900/20"
                    onClick={() => handleArchive(notice)}
                  >
                    <Trash2 size={14} /> Archive
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </Card>

      <CreateAnnouncementModal
        open={showCreate}
        onClose={() => {
          if (publishing) return;
          setShowCreate(false);
          setAnnouncementDraft(null);
        }}
        onPublish={handlePublish}
        audienceOptions={audienceOptions}
        initialValues={announcementDraft}
        templateOptions={announcementTemplates}
        submitting={publishing}
        uploadProgress={uploadProgress}
      />
    </>
  );
}
