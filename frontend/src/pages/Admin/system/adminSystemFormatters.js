export function formatUptime(seconds) {
  if (!seconds && seconds !== 0) return '-';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}h ${m}m ${s}s`;
}

export function formatDuration(value) {
  if (value === null || value === undefined) return '-';
  return `${value} ms`;
}

export function formatPercent(value) {
  if (value === null || value === undefined) return '-';
  return `${Number(value).toFixed(2)}%`;
}

export function formatSeconds(value) {
  if (value === null || value === undefined) return '-';
  if (value < 60) return `${value}s`;
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}m ${seconds}s`;
}

export function formatMinutes(value) {
  if (value === null || value === undefined) return '-';
  if (value < 60) return `${value}m`;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
}

export function formatDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

export function pickBudgetStatus(value, warning, critical) {
  if (value === null || value === undefined) return 'unknown';
  if (critical !== null && critical !== undefined && value >= critical) return 'critical';
  if (warning !== null && warning !== undefined && value >= warning) return 'warning';
  return 'ok';
}

export function statusClasses(status) {
  if (status === 'critical') {
    return 'border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100';
  }
  if (status === 'warning') {
    return 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100';
  }
  if (status === 'ok') {
    return 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100';
  }
  return 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200';
}
