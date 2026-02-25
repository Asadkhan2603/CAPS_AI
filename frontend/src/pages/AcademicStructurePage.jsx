import { useEffect, useMemo, useState } from 'react';
import { BookOpen, Building2, CalendarDays, GraduationCap, Layers3, Plus, Search, School } from 'lucide-react';
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
  { key: 'faculties', label: 'Faculties', icon: Building2, addRoute: '/faculties', addLabel: 'Add New Faculty', feature: 'faculties' },
  { key: 'departments', label: 'Departments', icon: Building2, addRoute: '/departments', addLabel: 'Add New Department', feature: 'departments' },
  { key: 'programs', label: 'Programs', icon: BookOpen, addRoute: '/programs', addLabel: 'Add New Program', feature: 'programs' },
  { key: 'specializations', label: 'Specializations', icon: Layers3, addRoute: '/specializations', addLabel: 'Add New Specialization', feature: 'specializations' },
  { key: 'batches', label: 'Batches', icon: GraduationCap, addRoute: '/batches', addLabel: 'Add New Batch', feature: 'batches' },
  { key: 'semesters', label: 'Semesters', icon: CalendarDays, addRoute: '/semesters', addLabel: 'Add New Semester', feature: 'semesters' },
  {
    key: 'sections',
    label: 'Sections',
    icon: School,
    addRoute: '/sections',
    addLabel: 'Add New Section',
    feature: 'sections'
  }
];

export default function AcademicStructurePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('sections');
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
      const [facultiesRes, departmentsRes, programsRes, specializationsRes, batchesRes, semestersRes, sectionsRes] = await Promise.all([
        safeList('/faculties/'),
        safeList('/departments/'),
        safeList('/programs/'),
        safeList('/specializations/'),
        safeList('/batches/'),
        safeList('/semesters/'),
        safeList('/sections/')
      ]);
      setFaculties(facultiesRes);
      setDepartments(departmentsRes);
      setPrograms(programsRes);
      setSpecializations(specializationsRes);
      setBatches(batchesRes);
      setSemesters(semestersRes);
      setSections(sectionsRes);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load academic hierarchy');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setFaculties([]);
      setDepartments([]);
      setPrograms([]);
      setSpecializations([]);
      setBatches([]);
      setSemesters([]);
      setSections([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStructure();
  }, []);

  const tabRows = useMemo(() => {
    if (activeTab === 'faculties') {
      return faculties.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
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
    if (activeTab === 'programs') {
      return programs.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'specializations') {
      return specializations.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'batches') {
      return batches.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'semesters') {
      return semesters.map((item) => ({
        id: item.id,
        name: item.label,
        code: `S${item.semester_number}`,
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    return sections.map((item) => ({
      id: item.id,
      name: item.name,
      code: item.branch_name || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
    }));
  }, [activeTab, faculties, departments, programs, specializations, batches, semesters, sections]);

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
  const searchPlaceholder = `Search ${activeTab}...`;

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
