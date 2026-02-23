import { useEffect, useMemo, useState } from 'react';
import { BookOpen, Building2, GraduationCap, Layers3, Plus, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { FEATURE_ACCESS } from '../config/featureAccess';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';
import { canAccessFeature } from '../utils/permissions';

const TABS = [
  { key: 'courses', label: 'Courses', icon: BookOpen, addRoute: '/courses', addLabel: 'Add New Course', feature: 'courses' },
  {
    key: 'departments',
    label: 'Departments',
    icon: Building2,
    addRoute: '/departments',
    addLabel: 'Add New Department',
    feature: 'departments'
  },
  { key: 'branches', label: 'Branches', icon: Layers3, addRoute: '/branches', addLabel: 'Add New Branch', feature: 'branches' },
  { key: 'years', label: 'Academic Years', icon: GraduationCap, addRoute: '/years', addLabel: 'Add New Year', feature: 'years' }
];

export default function AcademicStructurePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [payload, setPayload] = useState({ university: null, courses: [] });
  const [departments, setDepartments] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('years');
  const [query, setQuery] = useState('');

  async function safeList(path) {
    try {
      const response = await apiClient.get(path, { params: { skip: 0, limit: 200 } });
      return response.data || [];
    } catch {
      return [];
    }
  }

  async function loadStructure() {
    setLoading(true);
    setError('');
    try {
      const [structureRes, departmentsRes, branchesRes] = await Promise.all([
        apiClient.get('/analytics/academic-structure'),
        safeList('/departments/'),
        safeList('/branches/')
      ]);
      setPayload(structureRes.data || { university: null, courses: [] });
      setDepartments(departmentsRes);
      setBranches(branchesRes);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load academic hierarchy');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setPayload({ university: null, courses: [] });
      setDepartments([]);
      setBranches([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStructure();
  }, []);

  const courses = payload.courses || [];
  const years = useMemo(
    () => courses.flatMap((course) => (course.years || []).map((year) => ({ ...year, course_name: course.name }))),
    [courses]
  );

  const tabRows = useMemo(() => {
    if (activeTab === 'courses') {
      return courses.map((item, idx) => ({
        id: item.id,
        name: item.name,
        code: item.code || `C${idx + 1}`,
        status: 'ACTIVE'
      }));
    }
    if (activeTab === 'departments') {
      return departments.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'branches') {
      return branches.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    return years.map((item, idx) => ({
      id: item.id,
      name: item.name,
      code: item.code || `Y${idx + 1}`,
      status: 'ACTIVE'
    }));
  }, [activeTab, branches, courses, departments, years]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return tabRows;
    return tabRows.filter((row) =>
      [row.name, row.code, row.status].some((v) => String(v || '').toLowerCase().includes(q))
    );
  }, [query, tabRows]);

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Name' },
      {
        key: 'code',
        label: 'Code',
        render: (row) => (
          <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {row.code}
          </span>
        )
      },
      {
        key: 'status',
        label: 'Status',
        render: (row) => (
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              row.status === 'ACTIVE'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/35 dark:text-emerald-300'
                : 'bg-rose-100 text-rose-700 dark:bg-rose-900/35 dark:text-rose-300'
            }`}
          >
            {row.status}
          </span>
        )
      }
    ],
    []
  );

  const activeTabMeta = TABS.find((tab) => tab.key === activeTab) || TABS[0];
  const canManageActiveTab = canAccessFeature(user, FEATURE_ACCESS[activeTabMeta.feature] || {});
  const searchPlaceholder = activeTab === 'years' ? 'Search years...' : `Search ${activeTab}...`;

  function handleBlockedRoute() {
    pushToast({
      title: 'Access Restricted',
      description: 'You can view the structure here, but only admins can manage this tab.',
      variant: 'info'
    });
  }

  return (
    <div className="space-y-5 page-fade">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Academic Structure</h1>
          <p className="mt-1 text-lg text-slate-500 dark:text-slate-400">Manage your university's core academic hierarchy.</p>
        </div>
        <button
          className="btn-primary !rounded-2xl !px-5 !py-3 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => (canManageActiveTab ? navigate(activeTabMeta.addRoute) : handleBlockedRoute())}
          disabled={!canManageActiveTab}
          title={!canManageActiveTab ? 'Only admin can manage this tab' : activeTabMeta.addLabel}
        >
          <Plus size={18} /> {activeTabMeta.addLabel}
        </button>
      </div>

      <Card className="!p-2">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-base font-semibold transition ${
                activeTab === tab.key
                  ? 'bg-white text-brand-700 shadow-soft ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700'
                  : 'text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              <tab.icon size={18} /> {tab.label}
            </button>
          ))}
        </div>
      </Card>

      <Card className="space-y-4">
        <label className="relative block max-w-xl">
          <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input !h-12 !rounded-2xl !pl-11"
            placeholder={searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>

        {loading ? <p className="text-sm text-slate-500">Loading structure...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <Table
          columns={columns}
          data={filteredRows}
          onEdit={canManageActiveTab ? () => navigate(activeTabMeta.addRoute) : undefined}
          onDelete={
            canManageActiveTab
              ? () =>
                  pushToast({
                    title: 'Use Dedicated Page',
                    description: `Delete ${activeTabMeta.label.toLowerCase()} from ${activeTabMeta.addRoute} page.`,
                    variant: 'info'
                  })
              : undefined
          }
        />
      </Card>
    </div>
  );
}
