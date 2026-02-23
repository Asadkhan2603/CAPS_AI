import { memo, useMemo, useState } from 'react';
import Modal from '../ui/Modal';
import PriorityBadge from './PriorityBadge';
import ExpiryIndicator from './ExpiryIndicator';

function scopeLabel(notice) {
  const normalized = notice.scope === 'class' ? 'section' : notice.scope;
  if (normalized === 'college') return 'College';
  return `${normalized[0].toUpperCase()}${normalized.slice(1)}`;
}

function AnnouncementCard({ notice, audienceText }) {
  const [viewerOpen, setViewerOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const isExpired = notice.expires_at ? new Date(notice.expires_at).getTime() <= Date.now() : false;
  const files = notice.images || [];

  const imageFiles = useMemo(
    () =>
      files.filter((item) => {
        const mime = String(item.mime_type || '').toLowerCase();
        return mime.startsWith('image/') || /\.(jpg|jpeg|png|webp)$/i.test(String(item.url || ''));
      }),
    [files]
  );
  const nonImageFiles = useMemo(() => files.filter((item) => !imageFiles.includes(item)), [files, imageFiles]);

  const primaryImage = imageFiles[0] || null;

  return (
    <article
      className={`rounded-2xl border bg-white p-4 transition hover:border-slate-300 dark:bg-slate-900 ${
        isExpired ? 'border-slate-200/70 opacity-75 dark:border-slate-800' : 'border-slate-200 dark:border-slate-800'
      }`}
    >
      {primaryImage ? (
        <button
          type="button"
          className="relative mb-3 block h-48 w-full overflow-hidden rounded-xl"
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

      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">{notice.title}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{notice.message}</p>
        </div>
        <PriorityBadge priority={notice.priority} />
      </div>

      {nonImageFiles.length > 0 ? (
        <div className="mb-2 flex flex-wrap gap-2">
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

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">{scopeLabel(notice)}</span>
        <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">{audienceText}</span>
        <ExpiryIndicator expiresAt={notice.expires_at} />
        <span>Created {notice.created_at ? new Date(notice.created_at).toLocaleString() : '-'}</span>
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
