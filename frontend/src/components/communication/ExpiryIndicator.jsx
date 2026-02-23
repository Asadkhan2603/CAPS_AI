function toDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export default function ExpiryIndicator({ expiresAt }) {
  const expiry = toDate(expiresAt);
  if (!expiry) {
    return <span className="text-xs text-slate-400">No expiry</span>;
  }

  const now = new Date();
  const diffMs = expiry.getTime() - now.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffMs <= 0) {
    return <span className="text-xs font-medium text-slate-400">Expired</span>;
  }

  if (diffHours <= 72) {
    return <span className="text-xs font-medium text-amber-600 dark:text-amber-400">Expiring soon</span>;
  }

  return <span className="text-xs text-slate-500">Expires {expiry.toLocaleString()}</span>;
}
