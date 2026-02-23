export default function PriorityBadge({ priority }) {
  const normalized = String(priority || 'normal').toLowerCase();
  const urgent = normalized === 'urgent';
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
        urgent
          ? 'border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-300'
          : 'border border-brand-200 bg-brand-50 text-brand-700 dark:border-brand-800 dark:bg-brand-900/20 dark:text-brand-300'
      }`}
    >
      {urgent ? 'Urgent' : 'Normal'}
    </span>
  );
}
