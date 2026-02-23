import React, { useEffect, useMemo, useState } from 'react';
import { Search, GraduationCap, BookOpen, Building2, Layers } from 'lucide-react';
import { Card, Table, Badge } from '../components/ui';
import { apiClient } from '../services/apiClient';

type TabKey = 'courses' | 'departments' | 'branches' | 'years';

interface Entity {
  id: string;
  name?: string;
  code?: string;
  label?: string;
  year_number?: number;
  is_active?: boolean;
}

const tabConfig: { id: TabKey; label: string; icon: any; endpoint: string }[] = [
  { id: 'courses', label: 'Courses', icon: BookOpen, endpoint: '/courses/' },
  { id: 'departments', label: 'Departments', icon: Building2, endpoint: '/departments/' },
  { id: 'branches', label: 'Branches', icon: Layers, endpoint: '/branches/' },
  { id: 'years', label: 'Academic Years', icon: GraduationCap, endpoint: '/years/' }
];

export const AcademicStructurePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('courses');
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');

  const activeEndpoint = useMemo(() => tabConfig.find((x) => x.id === activeTab)?.endpoint || '/courses/', [activeTab]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await apiClient.get(activeEndpoint, { params: { skip: 0, limit: 200 } });
        setEntities(res.data || []);
      } catch {
        setEntities([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeEndpoint]);

  const filtered = entities.filter((e) => {
    const text = `${e.name || ''} ${e.code || ''} ${e.label || ''}`.toLowerCase();
    return text.includes(query.toLowerCase());
  });

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Academic Structure</h1>
        <p className="text-slate-500">Read-only structure view from backend.</p>
      </header>

      <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-xl w-fit">
        {tabConfig.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={[
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            ].join(' ')}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      <Card>
        <div className="mb-6 relative max-w-sm w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Search ${activeTab}...`} className="input pl-10 text-sm" />
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-500">Loading...</div>
        ) : (
          <Table headers={['Name', 'Code/Label', 'Status']}>
            {filtered.map((entity) => (
              <tr key={entity.id} className="hover:bg-slate-50">
                <td className="px-4 py-4 font-semibold text-slate-900">{entity.name || `Year ${entity.year_number || ''}`}</td>
                <td className="px-4 py-4 text-slate-600">{entity.code || entity.label || '-'}</td>
                <td className="px-4 py-4"><Badge variant={entity.is_active === false ? 'error' : 'success'}>{entity.is_active === false ? 'Inactive' : 'Active'}</Badge></td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
};
