import { Menu, Moon, Sun, UserCircle2, ChevronDown, LogOut } from 'lucide-react';
import { useState } from 'react';
import Breadcrumb from './Breadcrumb';

export default function Topbar({ user, onOpenMobile, isDark, onToggleTheme, onLogout }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/85 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button className="btn-secondary !p-2 lg:hidden" onClick={onOpenMobile}>
            <Menu size={16} />
          </button>
          <div>
            <Breadcrumb />
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Academic Operations Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="btn-secondary !p-2" onClick={onToggleTheme}>
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          <div className="relative hidden sm:block">
            <button className="btn-secondary" onClick={() => setOpen((prev) => !prev)}>
              <UserCircle2 size={16} />
              <span>{user?.full_name}</span>
              <ChevronDown size={14} />
            </button>

            {open ? (
              <div className="absolute right-0 top-11 w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-soft dark:border-slate-700 dark:bg-slate-900">
                <p className="text-sm font-semibold">{user?.full_name}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
                <p className="mt-1 text-xs text-slate-500">Role: {user?.role}</p>
                <button className="btn-secondary mt-3 w-full justify-start" onClick={onLogout}>
                  <LogOut size={15} /> Logout
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
