import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  History, 
  UserCircle, 
  BarChart3, 
  BookOpen, 
  Users, 
  FileText, 
  Bell,
  Settings,
  LogOut,
  ChevronRight,
  GraduationCap
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { hasPermission } from '../../utils/permissions';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard', featureKey: 'DASHBOARD' },
  { icon: GraduationCap, label: 'Academic', path: '/academic-structure', featureKey: 'ACADEMIC_STRUCTURE' },
  { icon: FileText, label: 'Assignments', path: '/assignments', featureKey: 'ASSIGNMENTS' },
  { icon: UserCircle, label: 'Profile', path: '/profile', featureKey: 'PROFILE' },
];

export const Sidebar: React.FC = () => {
  const { logout, user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const visibleNavItems = navItems.filter((item) => hasPermission(user, item.featureKey));

  return (
    <aside className={cn(
      "bg-white border-r border-slate-200 h-screen sticky top-0 transition-all duration-300 flex flex-col",
      isCollapsed ? "w-20" : "w-64"
    )}>
      <div className="p-6 flex items-center gap-3 border-b border-slate-100">
        <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center text-white shrink-0">
          <GraduationCap size={24} />
        </div>
        {!isCollapsed && <span className="font-bold text-xl tracking-tight text-slate-900">CAPS AI</span>}
      </div>

      <nav className="flex-1 overflow-y-auto p-4 space-y-2">
        {visibleNavItems.map((item) => (
          <div key={item.path}>
            <NavLink
              to={item.path}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-all group",
                isActive 
                  ? "bg-brand-50 text-brand-700 font-medium" 
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <item.icon size={20} className={cn(
                "shrink-0",
                "group-hover:scale-110 transition-transform"
              )} />
              {!isCollapsed && <span className="flex-1">{item.label}</span>}
              {!isCollapsed && <ChevronRight size={16} className="opacity-0" />}
            </NavLink>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-100">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-600 hover:bg-red-50 hover:text-red-600 transition-all"
        >
          <LogOut size={20} />
          {!isCollapsed && <span className="font-medium">Logout</span>}
        </button>
      </div>
    </aside>
  );
};
