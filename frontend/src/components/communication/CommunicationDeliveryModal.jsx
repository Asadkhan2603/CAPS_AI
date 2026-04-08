import Modal from '../ui/Modal';

function formatTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function statusTone(status) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'read') return 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-900/20 dark:text-emerald-300';
  if (normalized === 'sent') return 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900/60 dark:bg-sky-900/20 dark:text-sky-300';
  if (normalized === 'failed') return 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-900/20 dark:text-rose-300';
  if (normalized === 'skipped') return 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-300';
  return 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-300';
}

function isRetryableEmailRow(item) {
  const status = String(item?.status || '').toLowerCase();
  return String(item?.channel || '').toLowerCase() === 'email' && (status === 'failed' || status === 'skipped');
}

function retryTargetKey(item) {
  return `${item?.target_user_id || ''}::${item?.target_email || ''}`;
}

export default function CommunicationDeliveryModal({
  open,
  onClose,
  onRefresh,
  onExport,
  onRetryAllEmail,
  onRetryRecipientEmail,
  loading = false,
  retryingTarget = '',
  error = '',
  details = null,
  title = 'Delivery Details'
}) {
  const summary = details?.summary || {};
  const email = summary.email || {};
  const inApp = summary.in_app || {};
  const items = Array.isArray(details?.items) ? details.items : [];
  const retryableItems = items.filter(isRetryableEmailRow);
  const retryingAll = retryingTarget === '*';

  return (
    <Modal open={open} title={title} onClose={onClose} size="large">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {details?.source_title || 'Communication Item'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {details?.source_public_id || details?.source_id || ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {onExport ? (
              <button type="button" className="btn-secondary" onClick={() => onExport()} disabled={loading || retryingAll}>
                Export CSV
              </button>
            ) : null}
            {onRetryAllEmail ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => onRetryAllEmail()}
                disabled={loading || retryableItems.length === 0 || retryingAll}
              >
                {retryingAll ? 'Retrying...' : `Retry Unsent Email (${retryableItems.length})`}
              </button>
            ) : null}
            <button type="button" className="btn-secondary" onClick={onRefresh} disabled={loading || retryingAll}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-900/20 dark:text-rose-300">
            {error}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Recipients</p>
            <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{summary.total_recipients || 0}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Read {summary.read_count || 0} | Unread {summary.unread_count || 0}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">In-App</p>
            <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{inApp.sent_count || 0}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Read {inApp.read_count || 0} | Pending {inApp.pending_count || 0}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Email</p>
            <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{email.sent_count || 0}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Failed {email.failed_count || 0} | Skipped {email.skipped_count || 0}
            </p>
          </div>
        </div>

        {loading && items.length === 0 ? <p className="text-sm text-slate-500">Loading delivery details...</p> : null}

        <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-900/80">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Recipient</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Channel</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Sent</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Read</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Details</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Error</th>
                {onRetryRecipientEmail ? <th className="px-4 py-3 text-left font-medium text-slate-500">Action</th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950">
              {items.length === 0 ? (
                <tr>
                  <td colSpan={onRetryRecipientEmail ? 8 : 7} className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
                    No delivery rows recorded yet.
                  </td>
                </tr>
              ) : null}
              {items.map((item, index) => (
                <tr key={`${item.channel}-${item.target_user_id || item.target_email || index}`}>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                    <div className="font-medium">{item.target_user_label || item.target_email || item.target_user_id || 'Unknown recipient'}</div>
                    {item.target_email && item.target_email !== item.target_user_label ? (
                      <div className="text-xs text-slate-500 dark:text-slate-400">{item.target_email}</div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 capitalize text-slate-600 dark:text-slate-300">{item.channel || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-semibold ${statusTone(item.status)}`}>
                      {item.status || 'pending'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{formatTimestamp(item.sent_at)}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{formatTimestamp(item.read_at)}</td>
                  <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                    {Object.keys(item.metadata || {}).length ? (
                      <div className="space-y-1">
                        {Object.entries(item.metadata).map(([key, value]) => (
                          <div key={key}>
                            <span className="font-medium text-slate-600 dark:text-slate-300">{key}:</span>{' '}
                            <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{item.error || '-'}</td>
                  {onRetryRecipientEmail ? (
                    <td className="px-4 py-3">
                      {isRetryableEmailRow(item) ? (
                        <button
                          type="button"
                          className="btn-secondary !px-3 !py-1.5 text-xs"
                          onClick={() => onRetryRecipientEmail(item)}
                          disabled={loading || retryingTarget === retryTargetKey(item) || retryingAll}
                        >
                          {retryingTarget === retryTargetKey(item) ? 'Retrying...' : 'Retry Email'}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400 dark:text-slate-500">-</span>
                      )}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Modal>
  );
}
