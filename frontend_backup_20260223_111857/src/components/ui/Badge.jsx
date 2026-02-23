import { cn } from '../../utils/cn';

const styles = {
  default: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
  success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  danger: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  info: 'bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-300'
};

export default function Badge({ children, variant = 'default' }) {
  return <span className={cn('rounded-full px-2.5 py-1 text-xs font-medium', styles[variant])}>{children}</span>;
}
