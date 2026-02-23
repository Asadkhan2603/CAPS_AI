import { Home, ChevronRight } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function Breadcrumb() {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
      <Home size={14} />
      <Link to="/dashboard" className="hover:text-brand-600">Dashboard</Link>
      {segments
        .filter((seg) => seg !== 'dashboard')
        .map((segment) => (
          <span key={segment} className="flex items-center gap-2">
            <ChevronRight size={14} />
            <span className="capitalize">{segment.replace('-', ' ')}</span>
          </span>
        ))}
    </div>
  );
}
