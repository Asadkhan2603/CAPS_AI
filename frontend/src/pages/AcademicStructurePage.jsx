import { useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
  Building2,
  CalendarDays,
  CalendarRange,
  ChevronRight,
  GraduationCap,
  Layers3,
  Library,
  Loader2,
  Pencil,
  Plus,
  School,
  Search,
  Users
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Modal from '../components/ui/Modal';
import { ACADEMIC_HIERARCHY_MODEL } from '../constants/academicHierarchy';
import { apiClient } from '../services/apiClient';
import { FEATURE_ACCESS } from '../config/featureAccess';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { listAllPages, listAllWithActiveStates } from '../services/paginatedLookups';
import { formatApiError } from '../utils/apiError';
import { canAccessFeature } from '../utils/permissions';

const LEVELS = [
  { key: 'universities', label: 'Universities', icon: Building2 },
  { key: 'faculties', label: 'Faculties', icon: Building2 },
  { key: 'departments', label: 'Departments', icon: Building2 },
  { key: 'programs', label: 'Programs', icon: BookOpen },
  { key: 'specializations', label: 'Specializations', icon: Layers3 },
  { key: 'batches', label: 'Batches', icon: GraduationCap },
  { key: 'semesters', label: 'Semesters', icon: CalendarDays },
  { key: 'sections', label: 'Sections', icon: School },
  { key: 'groups', label: 'Groups', icon: Users }
];

const CHILD_LEVELS_BY_LEVEL = {
  universities: ['faculties'],
  faculties: ['departments'],
  departments: ['programs'],
  programs: ['specializations', 'batches'],
  specializations: ['batches'],
  batches: ['semesters'],
  semesters: ['sections'],
  sections: ['groups'],
  groups: []
};

const FILTER_BY_CHILD_LEVEL = {
  faculties: 'university_id',
  departments: 'faculty_id',
  programs: 'department_id',
  specializations: 'program_id',
  batches: 'specialization_id',
  semesters: 'batch_id',
  sections: 'semester_id',
  groups: 'section_id'
};

const LIST_ENDPOINT_BY_LEVEL = {
  universities: '/universities/',
  faculties: '/faculties/',
  departments: '/departments/',
  programs: '/programs/',
  specializations: '/specializations/',
  batches: '/batches/',
  semesters: '/semesters/',
  sections: '/sections/',
  groups: '/groups/'
};

const EDIT_ENDPOINT_BY_LEVEL = {
  universities: '/universities',
  faculties: '/faculties',
  departments: '/departments',
  programs: '/programs',
  specializations: '/specializations',
  batches: '/batches',
  semesters: '/semesters',
  sections: '/sections',
  groups: '/groups'
};

const LEVELS_WITH_ACTIVE_FILTER = new Set([
  'universities',
  'faculties',
  'departments',
  'programs',
  'specializations',
  'batches',
  'semesters',
  'groups'
]);

const INDENT_STEP = 22;

function createEmptyChildCache() {
  return {
    faculties: {},
    departments: {},
    programs: {},
    specializations: {},
    batches: {},
    semesters: {},
    sections: {},
    groups: {}
  };
}

function singularizeLabel(label) {
  return label.endsWith('s') ? label.slice(0, -1) : label;
}

function normalizeNode(level, item) {
  if (level === 'universities') {
    return {
      id: item.id,
      level,
      name: item.university_name,
      code: item.university_id || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  if (level === 'semesters') {
    return {
      id: item.id,
      level,
      name: item.label,
      code: `S${item.semester_number}`,
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  if (level === 'sections') {
    return {
      id: item.id,
      level,
      name: item.name,
      code: '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  if (level === 'groups') {
    return {
      id: item.id,
      level,
      name: item.name,
      code: item.code || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  return {
    id: item.id,
    level,
    name: item.name,
    code: item.code || '-',
    status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
    raw: item
  };
}

function matchesQuery(node, q) {
  const text = q.trim().toLowerCase();
  if (!text) return true;
  return [node.name, node.code, node.status].some((value) =>
    String(value || '')
      .toLowerCase()
      .includes(text)
  );
}

export default function AcademicStructurePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();

  const [rootNodes, setRootNodes] = useState([]);
  const [childCache, setChildCache] = useState(() => createEmptyChildCache());
  const [expandedKeys, setExpandedKeys] = useState({});
  const [loadingKeys, setLoadingKeys] = useState({});
  const [loadingRoot, setLoadingRoot] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [rootSkip, setRootSkip] = useState(0);
  const [rootLimit, setRootLimit] = useState(50);

  const [editOpen, setEditOpen] = useState(false);
  const [editNode, setEditNode] = useState(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editValues, setEditValues] = useState({ name: '', code: '', status: 'ACTIVE' });

  const canSuperAdminManage = user?.role === 'admin' && (user?.admin_type || 'admin') === 'super_admin';
  const canCreateUniversity = canSuperAdminManage && canAccessFeature(user, FEATURE_ACCESS.universities || {});

  async function listAllForLevel(level, params = {}) {
    const path = LIST_ENDPOINT_BY_LEVEL[level];
    if (!path) return [];

    if (!LEVELS_WITH_ACTIVE_FILTER.has(level)) {
      return listAllPages(path, params);
    }

    return listAllWithActiveStates(path, params);
  }

  async function loadRootUniversities() {
    setLoadingRoot(true);
    setError('');
    try {
      const response = await apiClient.get('/universities/', {
        params: { skip: rootSkip, limit: rootLimit, is_active: undefined, q: query || undefined }
      });
      const items = Array.isArray(response.data) ? response.data : [];
      setRootNodes(items.map((item) => normalizeNode('universities', item)));
    } catch (err) {
      const message = formatApiError(err, 'Failed to load universities');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setRootNodes([]);
    } finally {
      setLoadingRoot(false);
    }
  }

  useEffect(() => {
    loadRootUniversities();
  }, [query, rootLimit, rootSkip]);

  function clearTreeState() {
    setChildCache(createEmptyChildCache());
    setExpandedKeys({});
    setLoadingKeys({});
  }

  async function refreshTree() {
    clearTreeState();
    await loadRootUniversities();
  }

  function nodeKey(level, id) {
    return `${level}:${id}`;
  }

  function getChildLevels(level) {
    return CHILD_LEVELS_BY_LEVEL[level] || [];
  }

  function getLevelMeta(level) {
    return LEVELS.find((item) => item.key === level) || LEVELS[0];
  }

  function getCachedChildren(level, parentId) {
    if (!level || !parentId) return [];
    return childCache[level]?.[parentId] || [];
  }

  function hasChildrenLoaded(level, parentId) {
    if (!level || !parentId) return false;
    return Object.prototype.hasOwnProperty.call(childCache[level] || {}, parentId);
  }

  function getChildParams(parentLevel, childLevel, parentId) {
    if (parentLevel === 'programs' && childLevel === 'batches') {
      return { program_id: parentId };
    }
    const filterKey = FILTER_BY_CHILD_LEVEL[childLevel];
    return filterKey ? { [filterKey]: parentId } : {};
  }

  function normalizeChildItems(parentLevel, childLevel, items) {
    const rows =
      parentLevel === 'programs' && childLevel === 'batches'
        ? items.filter((item) => !item.specialization_id)
        : items;
    return rows.map((item) => normalizeNode(childLevel, item));
  }

  function getChildLevelLabel(level) {
    const childLevels = getChildLevels(level);
    if (!childLevels.length) return '';
    return childLevels.map((childLevel) => getLevelMeta(childLevel).label.toLowerCase()).join(' or ');
  }

  async function ensureChildrenLoaded(parentLevel, parentNode) {
    const childLevels = getChildLevels(parentLevel);
    if (!childLevels.length) return;
    const parentId = parentNode.id;
    const pendingLevels = childLevels.filter((childLevel) => {
      const loadKey = nodeKey(childLevel, parentId);
      return !hasChildrenLoaded(childLevel, parentId) && !loadingKeys[loadKey];
    });
    if (!pendingLevels.length) return;

    setLoadingKeys((prev) => ({
      ...prev,
      ...Object.fromEntries(pendingLevels.map((childLevel) => [nodeKey(childLevel, parentId), true]))
    }));
    try {
      const results = await Promise.allSettled(
        pendingLevels.map(async (childLevel) => {
          const childItems = await listAllForLevel(childLevel, getChildParams(parentLevel, childLevel, parentId));
          return {
            childLevel,
            normalized: normalizeChildItems(parentLevel, childLevel, childItems)
          };
        })
      );

      setChildCache((prev) => {
        const next = { ...prev };
        results.forEach((result) => {
          if (result.status !== 'fulfilled') return;
          const { childLevel, normalized } = result.value;
          next[childLevel] = {
            ...next[childLevel],
            [parentId]: normalized
          };
        });
        return next;
      });

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') return;
        const childLevel = pendingLevels[index];
        const levelMeta = getLevelMeta(childLevel);
        const message = formatApiError(result.reason, `Failed to load ${levelMeta.label.toLowerCase()}`);
        pushToast({ title: 'Load failed', description: message, variant: 'error' });
      });
    } finally {
      setLoadingKeys((prev) => {
        const next = { ...prev };
        pendingLevels.forEach((childLevel) => {
          next[nodeKey(childLevel, parentId)] = false;
        });
        return next;
      });
    }
  }

  async function toggleNode(level, node) {
    const key = nodeKey(level, node.id);
    const expanded = Boolean(expandedKeys[key]);
    if (expanded) {
      setExpandedKeys((prev) => ({ ...prev, [key]: false }));
      return;
    }
    setExpandedKeys((prev) => ({ ...prev, [key]: true }));
    await ensureChildrenLoaded(level, node);
  }

  function toEditDefaults(node) {
    const level = node.level;
    const raw = node.raw || {};
    if (level === 'universities') {
      return {
        name: raw.university_name || node.name || '',
        code: raw.university_id || node.code || '',
        status: raw.is_active === false ? 'INACTIVE' : 'ACTIVE'
      };
    }
    if (level === 'semesters') {
      return {
        name: raw.label || node.name || '',
        code: String(raw.semester_number ?? ''),
        status: raw.is_active === false ? 'INACTIVE' : 'ACTIVE'
      };
    }
    if (level === 'sections') {
      return {
        name: raw.name || node.name || '',
        code: '',
        status: raw.is_active === false ? 'INACTIVE' : 'ACTIVE'
      };
    }
    if (level === 'groups') {
      return {
        name: raw.name || node.name || '',
        code: raw.code || node.code || '',
        status: raw.is_active === false ? 'INACTIVE' : 'ACTIVE'
      };
    }
    return {
      name: raw.name || node.name || '',
      code: raw.code || '',
      status: raw.is_active === false ? 'INACTIVE' : 'ACTIVE'
    };
  }

  function buildEditPayload(level, values) {
    const isActive = values.status === 'ACTIVE';

    if (level === 'universities') {
      return {
        university_name: values.name.trim(),
        university_id: values.code.trim(),
        is_active: isActive
      };
    }

    if (level === 'semesters') {
      const semesterNumber = Number(values.code);
      if (!Number.isInteger(semesterNumber) || semesterNumber < 1 || semesterNumber > 12) {
        throw new Error('Semester number must be an integer between 1 and 12.');
      }
      return {
        label: values.name.trim(),
        semester_number: semesterNumber,
        is_active: isActive
      };
    }

    if (level === 'sections') {
      return {
        name: values.name.trim(),
        is_active: isActive
      };
    }

    return {
      name: values.name.trim(),
      code: values.code.trim(),
      is_active: isActive
    };
  }

  function openEdit(node) {
    setEditNode(node);
    setEditValues(toEditDefaults(node));
    setEditOpen(true);
  }

  function closeEdit() {
    if (savingEdit) return;
    setEditOpen(false);
    setEditNode(null);
  }

  async function submitEdit(event) {
    event.preventDefault();
    if (!editNode?.id || !editNode?.level) return;

    if (!editValues.name.trim()) {
      pushToast({ title: 'Invalid data', description: 'Name is required.', variant: 'error' });
      return;
    }
    if (editNode.level !== 'sections' && !String(editValues.code || '').trim()) {
      pushToast({ title: 'Invalid data', description: 'Code is required.', variant: 'error' });
      return;
    }

    const endpoint = EDIT_ENDPOINT_BY_LEVEL[editNode.level];
    if (!endpoint) {
      pushToast({ title: 'Unsupported action', description: 'Edit is not configured for this node.', variant: 'error' });
      return;
    }

    setSavingEdit(true);
    try {
      const payload = buildEditPayload(editNode.level, editValues);
      await apiClient.put(`${endpoint}/${editNode.id}`, payload);
      const levelMeta = getLevelMeta(editNode.level);
      pushToast({
        title: 'Updated',
        description: `${singularizeLabel(levelMeta.label)} updated successfully.`,
        variant: 'success'
      });
      closeEdit();
      await refreshTree();
    } catch (err) {
      const message = err instanceof Error ? err.message : formatApiError(err, 'Failed to update node');
      pushToast({ title: 'Update failed', description: message, variant: 'error' });
    } finally {
      setSavingEdit(false);
    }
  }

  const visibleRootNodes = useMemo(() => rootNodes.filter((node) => matchesQuery(node, query)), [rootNodes, query]);

  function renderNode(level, node, depth) {
    const childLevels = getChildLevels(level);
    const childLevel = childLevels[0] || null;
    const isExpandable = childLevels.length > 0;
    const expanded = Boolean(expandedKeys[nodeKey(level, node.id)]);
    const loadingChildren = childLevels.some((nextLevel) => Boolean(loadingKeys[nodeKey(nextLevel, node.id)]));
    const children = childLevels.flatMap((nextLevel) => getCachedChildren(nextLevel, node.id));
    const filteredChildren = children.filter((item) => matchesQuery(item, query));
    const childrenLoaded = isExpandable ? childLevels.every((nextLevel) => hasChildrenLoaded(nextLevel, node.id)) : false;
    const levelMeta = getLevelMeta(level);
    const childLevelLabel = getChildLevelLabel(level) || getLevelMeta(childLevel || level).label.toLowerCase();

    return (
      <div key={nodeKey(level, node.id)} className="border-b border-slate-200 dark:border-slate-800">
        <div
          className={`grid grid-cols-[minmax(0,1fr)_170px_130px_86px] items-center gap-3 px-2 py-3 text-sm ${
            isExpandable ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900/60' : ''
          }`}
          onClick={isExpandable ? () => toggleNode(level, node) : undefined}
          role={isExpandable ? 'button' : undefined}
          tabIndex={isExpandable ? 0 : undefined}
          onKeyDown={
            isExpandable
              ? (event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    toggleNode(level, node);
                  }
                }
              : undefined
          }
        >
          <div className="flex min-w-0 items-center gap-2" style={{ paddingLeft: `${depth * INDENT_STEP + 8}px` }}>
            {isExpandable ? (
              <button
                className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={(event) => {
                  event.stopPropagation();
                  toggleNode(level, node);
                }}
              >
                {loadingChildren ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <ChevronRight size={16} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
                )}
              </button>
            ) : (
              <span className="px-1 text-slate-400">-</span>
            )}
            <levelMeta.icon size={14} className="text-slate-400" />
            <span className="truncate font-medium text-slate-800 dark:text-slate-100">{node.name}</span>
          </div>

          <div>
            <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {node.code}
            </span>
          </div>

          <div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                node.status === 'ACTIVE'
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/35 dark:text-emerald-300'
                  : 'bg-rose-100 text-rose-700 dark:bg-rose-900/35 dark:text-rose-300'
              }`}
            >
              {node.status}
            </span>
          </div>

          <div className="flex justify-end">
            {canSuperAdminManage ? (
              <button
                className="btn-secondary !p-2"
                onClick={(event) => {
                  event.stopPropagation();
                  openEdit(node);
                }}
                title={`Edit ${singularizeLabel(levelMeta.label)}`}
              >
                <Pencil size={15} />
              </button>
            ) : null}
          </div>
        </div>

        {isExpandable ? (
          <AnimatePresence initial={false}>
            {expanded ? (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
                className="overflow-hidden"
              >
                {loadingChildren ? (
                  <p className="px-6 pb-3 text-xs text-slate-500">
                    Loading {childLevelLabel}...
                  </p>
                ) : null}

                {!loadingChildren && childrenLoaded && filteredChildren.length === 0 ? (
                  <p className="px-6 pb-3 text-xs text-slate-500">
                    No {childLevelLabel} found under this {singularizeLabel(levelMeta.label).toLowerCase()}.
                  </p>
                ) : null}

                {!loadingChildren && filteredChildren.map((childNode) => renderNode(childNode.level, childNode, depth + 1))}
              </motion.div>
            ) : null}
          </AnimatePresence>
        ) : null}
      </div>
    );
  }

  const editLevelMeta = editNode ? getLevelMeta(editNode.level) : null;
  const editSingularLabel = editLevelMeta ? singularizeLabel(editLevelMeta.label) : 'Node';
  const editCodeLabel = editNode?.level === 'semesters' ? 'Semester Number' : 'Code';
  const editCodeType = editNode?.level === 'semesters' ? 'number' : 'text';

  return (
    <div className="space-y-5 page-fade">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Academic Structure</h1>
          <p className="mt-1 text-lg text-slate-500 dark:text-slate-400">
            {ACADEMIC_HIERARCHY_MODEL}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary !rounded-2xl !px-4 !py-3" onClick={refreshTree}>
            Refresh
          </button>
          <button
            className="btn-primary !rounded-2xl !px-5 !py-3 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => navigate('/universities')}
            disabled={!canCreateUniversity}
            title={!canCreateUniversity ? 'Only super admin can add from this panel' : 'Add New University'}
          >
            <Plus size={18} /> Add New University
          </button>
        </div>
      </div>

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
            Academic Model
          </span>
          <span className="text-sm text-slate-500 dark:text-slate-400">
            Universities own faculties, programs can create direct batches or specialization-specific batches, and semester delivery is handled through course delivery and class slots.
          </span>
        </div>
        <div className="space-y-2 text-sm font-medium text-slate-700 dark:text-slate-200">
          <div className="flex flex-wrap items-center gap-2">
            {['University', 'Faculty', 'Department', 'Program', 'Batch', 'Semester', 'Section', 'Group'].map((item, index, items) => (
              <div key={item} className="flex items-center gap-2">
                <span className="rounded-2xl bg-slate-100 px-3 py-1.5 dark:bg-slate-800">{item}</span>
                {index < items.length - 1 ? <ChevronRight size={14} className="text-slate-400" /> : null}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-slate-500 dark:text-slate-400">
            {['Program', 'Specialization', 'Batch'].map((item, index, items) => (
              <div key={item} className="flex items-center gap-2">
                <span className="rounded-2xl bg-slate-100 px-3 py-1.5 dark:bg-slate-800">{item}</span>
                {index < items.length - 1 ? <ChevronRight size={14} className="text-slate-400" /> : null}
              </div>
            ))}
            <span className="ml-1 text-xs font-semibold uppercase tracking-[0.18em]">Optional Track</span>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-900/70">
          <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
            <span className="rounded-2xl bg-white px-3 py-1.5 dark:bg-slate-950">Semester</span>
            <ChevronRight size={14} className="text-slate-400" />
            <span className="rounded-2xl bg-white px-3 py-1.5 dark:bg-slate-950">Course Delivery</span>
            <ChevronRight size={14} className="text-slate-400" />
            <span className="rounded-2xl bg-white px-3 py-1.5 dark:bg-slate-950">Class Slots</span>
          </div>
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
            Use the delivery layer to manage subject allocation, teacher assignment, practicals, tutorials, and timetable slots inside each semester.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <button type="button" className="btn-secondary justify-start" onClick={() => navigate('/sections')}>
              <School size={16} /> Manage Sections
            </button>
            <button type="button" className="btn-secondary justify-start" onClick={() => navigate('/groups')}>
              <Users size={16} /> Manage Groups
            </button>
            <button type="button" className="btn-secondary justify-start" onClick={() => navigate('/course-offerings')}>
              <Library size={16} /> Manage Course Delivery
            </button>
            <button type="button" className="btn-secondary justify-start" onClick={() => navigate('/class-slots')}>
              <CalendarRange size={16} /> Manage Class Slots
            </button>
          </div>
        </div>
      </Card>

      <Card className="space-y-4">
        <label className="relative block max-w-xl">
          <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input !h-12 !rounded-2xl !pl-11"
            placeholder="Search loaded academic hierarchy..."
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setRootSkip(0);
            }}
          />
        </label>

        {loadingRoot ? <p className="text-sm text-slate-500">Loading universities...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900">
          <div className="grid grid-cols-[minmax(0,1fr)_170px_130px_86px] items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600 dark:border-slate-800 dark:bg-slate-800/70 dark:text-slate-200">
            <span>Name</span>
            <span>Code</span>
            <span>Status</span>
            <span className="text-right">Actions</span>
          </div>

          {visibleRootNodes.length === 0 && !loadingRoot ? (
            <div className="px-4 py-8 text-center text-sm text-slate-500">No records found.</div>
          ) : (
            <div>{visibleRootNodes.map((node) => renderNode('universities', node, 0))}</div>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button type="button" className="btn-secondary" disabled={rootSkip === 0} onClick={() => setRootSkip(Math.max(0, rootSkip - rootLimit))}>
            Prev
          </button>
          <span className="text-xs text-slate-500">skip: {rootSkip}</span>
          <button type="button" className="btn-secondary" disabled={rootNodes.length < rootLimit} onClick={() => setRootSkip(rootSkip + rootLimit)}>
            Next
          </button>
          <select className="input w-24" value={rootLimit} onChange={(event) => { setRootLimit(Number(event.target.value)); setRootSkip(0); }}>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </Card>

      <Modal open={editOpen} title={`Edit ${editSingularLabel}`} onClose={closeEdit}>
        <form className="space-y-4" onSubmit={submitEdit}>
          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</span>
            <input
              className="input"
              value={editValues.name}
              onChange={(event) => setEditValues((prev) => ({ ...prev, name: event.target.value }))}
              placeholder={`Enter ${editSingularLabel.toLowerCase()} name`}
              required
            />
          </label>

          {editNode?.level !== 'sections' ? (
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{editCodeLabel}</span>
              <input
                className="input"
                type={editCodeType}
                value={editValues.code}
                onChange={(event) => setEditValues((prev) => ({ ...prev, code: event.target.value }))}
                placeholder={editNode?.level === 'semesters' ? '1 - 12' : `Enter ${editCodeLabel.toLowerCase()}`}
                required
              />
            </label>
          ) : null}

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</span>
            <select
              className="input"
              value={editValues.status}
              onChange={(event) => setEditValues((prev) => ({ ...prev, status: event.target.value }))}
            >
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>
          </label>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button className="btn-secondary" type="button" onClick={closeEdit} disabled={savingEdit}>
              Cancel
            </button>
            <button className="btn-primary" type="submit" disabled={savingEdit}>
              {savingEdit ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

