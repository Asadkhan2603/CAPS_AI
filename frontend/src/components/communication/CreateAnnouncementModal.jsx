import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Paperclip, X } from 'lucide-react';
import Modal from '../ui/Modal';
import AudienceSelector from './AudienceSelector';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

const MAX_ATTACHMENTS = 3;
const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
  'application/pdf',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

function formatFileSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export default function CreateAnnouncementModal({
  open,
  onClose,
  onPublish,
  audienceOptions,
  canPreviewAudience = false,
  initialValues = null,
  templateOptions = [],
  submitting = false,
  uploadProgress = 0
}) {
  const [step, setStep] = useState(1);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [urgent, setUrgent] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [audienceKey, setAudienceKey] = useState('');
  const [templateKey, setTemplateKey] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [autoExpire, setAutoExpire] = useState(false);
  const [expiresAt, setExpiresAt] = useState('');
  const [scheduleForLater, setScheduleForLater] = useState(false);
  const [scheduledAt, setScheduledAt] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [attachmentError, setAttachmentError] = useState('');
  const [audiencePreview, setAudiencePreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');

  const selectedAudience = useMemo(
    () => audienceOptions.find((item) => item.key === audienceKey) || null,
    [audienceKey, audienceOptions]
  );
  const attachmentPreviews = useMemo(
    () =>
      attachments.map((file) => ({
        file,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : '',
      })),
    [attachments]
  );

  useEffect(
    () => () => {
      attachmentPreviews.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
    },
    [attachmentPreviews]
  );

  useEffect(() => {
    if (!open) return;
    setStep(1);
    setTitle(initialValues?.title || '');
    setMessage(initialValues?.message || '');
    setUrgent(Boolean(initialValues?.priority === 'urgent'));
    setPinned(Boolean(initialValues?.is_pinned));
    setAudienceKey(audienceOptions[0]?.key || '');
    setTemplateKey(initialValues?.template_key || '');
    setShowAdvanced(false);
    setAutoExpire(false);
    setExpiresAt('');
    setScheduleForLater(false);
    setScheduledAt('');
    setAttachments([]);
    setAttachmentError('');
    setAudiencePreview(null);
    setPreviewLoading(false);
    setPreviewError('');
  }, [audienceOptions, initialValues, open]);

  useEffect(() => {
    let alive = true;

    async function loadAudiencePreview() {
      if (!open || !selectedAudience || !canPreviewAudience) {
        if (alive) {
          setAudiencePreview(null);
          setPreviewError('');
        }
        return;
      }
      setPreviewLoading(true);
      setPreviewError('');
      try {
        const response = await apiClient.post('/admin/communication/preview-target', {
          scope: selectedAudience.scope,
          scope_ref_id: selectedAudience.scopeRefId
        });
        if (!alive) return;
        setAudiencePreview(response.data || null);
      } catch (error) {
        if (!alive) return;
        setAudiencePreview(null);
        setPreviewError(formatApiError(error, 'Unable to estimate audience reach right now.'));
      } finally {
        if (alive) {
          setPreviewLoading(false);
        }
      }
    }

    void loadAudiencePreview();
    return () => {
      alive = false;
    };
  }, [canPreviewAudience, open, selectedAudience]);

  const scheduleError = useMemo(() => {
    if (!scheduleForLater || !scheduledAt) return '';
    const scheduledTime = new Date(scheduledAt).getTime();
    if (Number.isNaN(scheduledTime)) return 'Choose a valid future schedule.';
    if (scheduledTime <= Date.now()) return 'Scheduled publish time must be in the future.';
    return '';
  }, [scheduleForLater, scheduledAt]);

  const canProceedStep1 = title.trim().length >= 2 && message.trim().length >= 2 && !attachmentError;
  const canPublish =
    canProceedStep1 &&
    selectedAudience &&
    (!autoExpire || Boolean(expiresAt)) &&
    (!scheduleForLater || (Boolean(scheduledAt) && !scheduleError));

  function onFilesSelected(event) {
    const nextFiles = Array.from(event.target.files || []);
    if (nextFiles.length === 0) return;

    setAttachmentError('');
    const merged = [...attachments];

    for (const file of nextFiles) {
      if (merged.length >= MAX_ATTACHMENTS) {
        setAttachmentError(`Only ${MAX_ATTACHMENTS} attachments are allowed.`);
        break;
      }
      if (!ACCEPTED_TYPES.includes((file.type || '').toLowerCase())) {
        setAttachmentError('Only JPG, JPEG, PNG, WEBP, PDF, XLS, XLSX files are allowed.');
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setAttachmentError('Each attachment must be 10MB or smaller.');
        continue;
      }
      merged.push(file);
    }

    setAttachments(merged);
    event.target.value = '';
  }

  function removeAttachment(index) {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
    setAttachmentError('');
  }

  function submit() {
    if (!canPublish || submitting) return;
    onPublish({
      title: title.trim(),
      message: message.trim(),
      priority: urgent ? 'urgent' : 'normal',
      is_pinned: pinned,
      template_key: templateKey || null,
      scope: selectedAudience.scope,
      scope_ref_id: selectedAudience.scopeRefId,
      expires_at: autoExpire && expiresAt ? new Date(expiresAt).toISOString() : null,
      scheduled_at: scheduleForLater && scheduledAt ? new Date(scheduledAt).toISOString() : null,
      attachments,
    });
  }

  return (
    <Modal open={open} title="New Announcement" onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-xs">
          {[1, 2, 3].map((n) => (
            <span
              key={n}
              className={`rounded-full px-2.5 py-1 font-medium ${
                step === n
                  ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                  : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300'
              }`}
            >
              Step {n}
            </span>
          ))}
        </div>

        {step === 1 ? (
          <div className="space-y-3">
            <label className="block space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</span>
              <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Announcement title" />
            </label>

            <label className="block space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Message</span>
              <textarea
                className="input min-h-28 resize-y"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Write clear message content"
              />
            </label>

            <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
              <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} />
              Mark as urgent
            </label>

            {templateOptions.length ? (
              <label className="block space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Template</span>
                <select
                  className="input"
                  value={templateKey}
                  onChange={(e) => setTemplateKey(e.target.value)}
                >
                  <option value="">Custom</option>
                  {templateOptions.map((option) => (
                    <option key={option.key} value={option.key}>{option.label}</option>
                  ))}
                </select>
              </label>
            ) : null}

            <div className="space-y-2 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Attachments (optional)</p>
                <label className="btn-secondary cursor-pointer !px-3 !py-1.5 text-xs">
                  <Paperclip size={14} /> Add files
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    accept=".jpg,.jpeg,.png,.webp,.pdf,.xls,.xlsx"
                    onChange={onFilesSelected}
                  />
                </label>
              </div>

              {attachmentError ? <p className="text-xs text-rose-600">{attachmentError}</p> : null}

              {attachments.length > 0 ? (
                <div className="space-y-2">
                  {attachmentPreviews.map(({ file, previewUrl }, index) => {
                    const isImage = Boolean(previewUrl);
                    return (
                      <div key={`${file.name}-${index}`} className="flex items-center gap-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
                        {isImage ? (
                          <img src={previewUrl} alt={file.name} className="h-12 w-16 rounded-md object-cover" />
                        ) : (
                          <div className="grid h-12 w-16 place-items-center rounded-md bg-slate-100 text-xs text-slate-500 dark:bg-slate-800">FILE</div>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-slate-700 dark:text-slate-200">{file.name}</p>
                          <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
                        </div>
                        <button type="button" className="btn-secondary !p-1.5" onClick={() => removeAttachment(index)}>
                          <X size={14} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-xs text-slate-500">Up to 3 files, 10MB each.</p>
              )}
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-3">
            <AudienceSelector options={audienceOptions} value={audienceKey} onChange={(item) => setAudienceKey(item.key)} />
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
              <p className="font-semibold text-slate-900 dark:text-slate-100">Audience reach preview</p>
              {previewLoading ? <p className="mt-1 text-slate-500">Estimating recipients...</p> : null}
              {!previewLoading && previewError ? <p className="mt-1 text-rose-600">{previewError}</p> : null}
              {!previewLoading && !previewError && audiencePreview ? (
                <p className="mt-1 text-slate-600 dark:text-slate-300">
                  Estimated recipients: <span className="font-semibold text-slate-900 dark:text-slate-100">{audiencePreview.estimated_reach ?? audiencePreview.matched_users ?? 0}</span>
                </p>
              ) : null}
              {!previewLoading && !previewError && !audiencePreview ? (
                <p className="mt-1 text-slate-500">Select an audience to preview recipient reach.</p>
              ) : null}
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
              <p className="font-semibold text-slate-900 dark:text-slate-100">Publishing summary</p>
              <p className="mt-1 text-slate-600 dark:text-slate-300">
                Audience: <span className="font-medium">{selectedAudience?.label || 'Not selected'}</span>
                {audiencePreview ? ` | Estimated recipients: ${audiencePreview.estimated_reach ?? audiencePreview.matched_users ?? 0}` : ''}
              </p>
            </div>

            <button
              type="button"
              className="flex w-full items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
              onClick={() => setShowAdvanced((prev) => !prev)}
            >
              <span>Advanced Options</span>
              {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showAdvanced ? (
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <label className="inline-flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={autoExpire} onChange={(e) => setAutoExpire(e.target.checked)} />
                  Auto-expire
                </label>

                <label className="mt-3 inline-flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} />
                  Pin announcement to the top
                </label>

                <label className="mt-3 inline-flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={scheduleForLater} onChange={(e) => setScheduleForLater(e.target.checked)} />
                  Schedule for later
                </label>

                {autoExpire ? (
                  <label className="mt-3 block space-y-1">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Expires At</span>
                    <input type="datetime-local" className="input" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
                  </label>
                ) : null}

                {scheduleForLater ? (
                  <label className="mt-3 block space-y-1">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Publish At</span>
                    <input type="datetime-local" className="input" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
                    {scheduleError ? <span className="text-xs text-rose-600">{scheduleError}</span> : null}
                  </label>
                ) : null}
              </div>
            ) : (
              <p className="text-xs text-slate-500">Optional settings are collapsed by default.</p>
            )}
          </div>
        ) : null}

        {submitting ? (
          <div className="space-y-1">
            <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
              <div className="h-full bg-brand-600 transition-all" style={{ width: `${Math.max(2, uploadProgress)}%` }} />
            </div>
            <p className="text-xs text-slate-500">Uploading {uploadProgress}%</p>
          </div>
        ) : null}

        <div className="flex items-center justify-between gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
          <button className="btn-secondary" type="button" onClick={onClose}>
            Cancel
          </button>

          <div className="flex items-center gap-2">
            {step > 1 ? (
              <button className="btn-secondary" type="button" onClick={() => setStep((s) => s - 1)} disabled={submitting}>
                Back
              </button>
            ) : null}

            {step < 3 ? (
              <button className="btn-primary" type="button" onClick={() => setStep((s) => s + 1)} disabled={step === 1 && !canProceedStep1}>
                Continue
              </button>
            ) : (
              <button className="btn-primary" type="button" onClick={submit} disabled={!canPublish || submitting}>
                {submitting ? 'Publishing...' : scheduleForLater ? 'Schedule Announcement' : 'Publish'}
              </button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
