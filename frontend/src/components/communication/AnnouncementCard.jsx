import { memo, useMemo, useState } from 'react';
import { Newspaper, Megaphone } from 'lucide-react';
import Modal from '../ui/Modal';
import PriorityBadge from './PriorityBadge';
import ExpiryIndicator from './ExpiryIndicator';

function scopeLabel(notice) {
  const normalized = notice.scope === 'class' ? 'section' : notice.scope;
  if (normalized === 'college') return 'College';
  return `${normalized[0].toUpperCase()}${normalized.slice(1)}`;
}

function formatRelativeTime(value) {
  if (!value) return 'just now';
  const ts = new Date(value).getTime();
  if (Number.isNaN(ts)) return 'just now';
  const deltaMs = Date.now() - ts;
  if (deltaMs < 60 * 1000) return 'just now';
  const minutes = Math.floor(deltaMs / (60 * 1000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days > 1 ? 's' : ''} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months > 1 ? 's' : ''} ago`;
  const years = Math.floor(months / 12);
  return `${years} year${years > 1 ? 's' : ''} ago`;
}

function postedByLabel(notice) {
  const direct = notice.created_by_name || notice.created_by_full_name || notice.author_name;
  if (direct) return String(direct).toUpperCase();
  return 'SYSTEM';
}

function normalizeFiles(notice) {
  const raw = notice.images || notice.attachments || [];
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (typeof item === 'string') {
        return { url: item, name: 'Attachment', mime_type: '' };
      }
      return {
        ...item,
        url: item?.url || item?.secure_url || item?.path || '',
      };
    })
    .filter((item) => Boolean(item.url));
}

function AnnouncementCard({ notice, audienceText, isRead = false, onMarkRead }) {
  const [viewerOpen, setViewerOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);

  const isExpired = notice.expires_at ? new Date(notice.expires_at).getTime() <= Date.now() : false;
  const files = useMemo(() => normalizeFiles(notice), [notice]);

  const imageFiles = useMemo(
    () =>
      files.filter((item) => {
        const mime = String(item.mime_type || item.type || '').toLowerCase();
        return mime.startsWith('image/') || /\.(jpg|jpeg|png|webp)(\?|#|$)/i.test(String(item.url || ''));
      }),
    [files]
  );
  const nonImageFiles = useMemo(() => files.filter((item) => !imageFiles.includes(item)), [files, imageFiles]);

  const primaryImage = imageFiles[0] || null;
  const messageText = String(notice.message || '');
  const shouldTruncate = messageText.length > 220;
  const previewText = shouldTruncate && !expanded ? `${messageText.slice(0, 220).trim()}...` : messageText;

  return (
    <article
      className={`rounded-2xl border bg-white p-4 transition hover:border-slate-300 dark:bg-slate-900 ${
        isExpired ? 'border-slate-200/70 opacity-75 dark:border-slate-800' : 'border-slate-200 dark:border-slate-800'
      }`}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/35 dark:text-brand-300">
            <Newspaper size={20} />
          </div>
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-500 dark:text-slate-400">
              POST BY {postedByLabel(notice)}
            </p>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  isRead
                    ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                    : 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                }`}
              >
                {isRead ? 'Read' : 'Unread'}
              </span>
              <PriorityBadge priority={notice.priority} />
            </div>
          </div>
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400">{formatRelativeTime(notice.created_at)}</span>
      </div>

      <h3 className="text-2xl font-semibold text-slate-900 dark:text-white">{notice.title}</h3>
      <div className="mt-3">
        <Megaphone size={24} className="text-brand-600 dark:text-brand-300" />
      </div>
      <p className="mt-2 whitespace-pre-line break-words text-base leading-8 text-slate-700 dark:text-slate-200">
        {previewText}
        {shouldTruncate ? (
          <button
            type="button"
            className="ml-1 text-brand-700 hover:underline dark:text-brand-300"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? 'less' : 'more'}
          </button>
        ) : null}
      </p>

      {primaryImage ? (
        <button
          type="button"
          className="relative mt-4 block h-72 w-full overflow-hidden rounded-xl"
          onClick={() => {
            setActiveIndex(0);
            setViewerOpen(true);
          }}
        >
          <img src={primaryImage.url} alt={notice.title} className="h-full w-full object-cover" loading="lazy" />
          {imageFiles.length > 1 ? (
            <span className="absolute bottom-2 right-2 rounded-full bg-slate-900/75 px-2 py-1 text-xs text-white">
              +{imageFiles.length - 1} more
            </span>
          ) : null}
        </button>
      ) : null}

      {nonImageFiles.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {nonImageFiles.map((file) => (
            <a
              key={file.public_id || file.url}
              href={file.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {file.name || 'Attachment'}
            </a>
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">{scopeLabel(notice)}</span>
        <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">{audienceText}</span>
        <ExpiryIndicator expiresAt={notice.expires_at} />
        <span className="inline-flex items-center gap-1">
          <Megaphone size={12} />
          Announcement
        </span>
        {!isRead && onMarkRead ? (
          <button
            type="button"
            className="rounded-md border border-brand-200 px-2 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-50 dark:border-brand-800 dark:text-brand-300 dark:hover:bg-brand-900/25"
            onClick={() => onMarkRead(notice.id)}
          >
            Mark read
          </button>
        ) : null}
      </div>

      <Modal open={viewerOpen} title="Attachment Preview" onClose={() => setViewerOpen(false)}>
        {imageFiles.length === 0 ? (
          <p className="text-sm text-slate-500">No image attachments.</p>
        ) : (
          <div className="space-y-3">
            <img src={imageFiles[activeIndex]?.url} alt={`Image ${activeIndex + 1}`} className="max-h-[70vh] w-full rounded-xl object-contain" loading="lazy" />
            <div className="flex items-center justify-between">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveIndex((idx) => Math.max(0, idx - 1))}
                disabled={activeIndex === 0}
              >
                Prev
              </button>
              <span className="text-xs text-slate-500">
                {activeIndex + 1} / {imageFiles.length}
              </span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveIndex((idx) => Math.min(imageFiles.length - 1, idx + 1))}
                disabled={activeIndex >= imageFiles.length - 1}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Modal>
    </article>
  );
}

export default memo(AnnouncementCard);
