import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { cn } from '../../utils/cn';
import Card from './Card';

export default function StatCard({ icon: Icon, title, value, hint, gradient = 'from-brand-600 to-blue-500', to }) {
  const content = (
    <Card className={cn('relative overflow-hidden', to && 'cursor-pointer transition hover:shadow-md')}>
      <div className={cn('absolute inset-x-0 top-0 h-1 bg-gradient-to-r', gradient)} />
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{value}</p>
          {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
        </div>
        {Icon ? (
          <div className="rounded-2xl bg-brand-50 p-3 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300">
            <Icon size={20} />
          </div>
        ) : null}
      </div>
    </Card>
  );

  return (
    <motion.div whileHover={{ y: -4, scale: 1.01 }} transition={{ type: 'spring', stiffness: 260, damping: 18 }}>
      {to ? <Link to={to}>{content}</Link> : content}
    </motion.div>
  );
}
