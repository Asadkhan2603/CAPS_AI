import { useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
  Building2,
  CalendarDays,
  ChevronRight,
  GraduationCap,
  Layers3,
  Loader2,
  Pencil,
  Plus,
  School,
  Search
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Modal from '../components/ui/Modal';
import { apiClient } from '../services/apiClient';
import { FEATURE_ACCESS } from '../config/featureAccess';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';
import { canAccessFeature } from '../utils/permissions';

const LEVELS = [
  { key: 'faculties', label: 'Faculties', icon: Building2 },
  { key: 'departments', label: 'Departments', icon: Building2 },
  { key: 'programs', label: 'Programs', icon: BookOpen },
  { key: 'specializations', label: 'Specializations', icon: Layers3 },
  { key: 'batches', label: 'Batches', icon: GraduationCap },
  { key: 'semesters', label: 'Semesters', icon: CalendarDays },
  { key: 'sections', label: 'Sections', icon: School }
];

const CHILD_LEVEL_BY_LEVEL = {
  faculties: 'departments',
  departments: 'programs',
  programs: 'specializations',
  specializations: 'batches',
  batches: 'semesters',
  semesters: 'sections',
  sections: null
};

const FILTER_BY_CHILD_LEVEL = {
  departments: 'faculty_id',
  programs: 'department_id',
  specializations: 'program_id',
  batches: 'specialization_id',
  semesters: 'batch_id',
  sections: 'semester_id'
};

const LIST_ENDPOINT_BY_LEVEL = {
  faculties: '/faculties/',
  departments: '/departments/',
  programs: '/programs/',
  specializations: '/specializations/',
  batches: '/batches/',
  semesters: '/semesters/',
  sections: '/sections/'
};

const EDIT_ENDPOINT_BY_LEVEL = {
  faculties: '/faculties',
  departments: '/departments',
  programs: '/programs',
  specializations: '/specializations',
  batches: '/batches',
  semesters: '/semesters',
  sections: '/sections'
};

const LEVELS_WITH_ACTIVE_FILTER = new Set([
  'faculties',
  'departments',
  'programs',
  'specializations',
  'batches',
  'semesters'
]);

const PAGE_SIZE = 100;
const MAX_PAGES = 20;
const INDENT_STEP = 22;

function createEmptyChildCache() {
  return {
    departments: {},
    programs: {},
    specializations: {},
    batches: {},
    semesters: {},
    sections: {}
  };
}

function singularizeLabel(label) {
  return label.endsWith('s') ? label.slice(0, -1) : label;
}

function normalizeNode(level, item) {
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
      code: item.branch_name || '-',
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

  const [faculties, setFaculties] = useState([]);
  const [childCache, setChildCache] = useState(() => createEmptyChildCache());
  const [expandedKeys, setExpandedKeys] = useState({});
  const [loadingKeys, setLoadingKeys] = useState({});
  const [loadingRoot, setLoadingRoot] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  const [editOpen, setEditOpen] = useState(false);
  const [editNode, setEditNode] = useState(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editValues, setEditValues] = useState({ name: '', code: '', status: 'ACTIVE' });

  const canSuperAdminManage = user?.role === 'admin' && (user?.admin_type || 'admin') === 'super_admin';
  const canCreateFaculty = canSuperAdminManage && canAccessFeature(user, FEATURE_ACCESS.faculties || {});

  async function listAll(path, params = {}) {
    const collected = [];
    for (let page = 0; page < MAX_PAGES; page += 1) {
      const response = await apiClient.get(path, {
        params: { ...params, skip: page * PAGE_SIZE, limit: PAGE_SIZE }
      });
      const items = Array.isArray(response.data) ? response.data : [];
      collected.push(...items);
      if (items.length < PAGE_SIZE) break;
    }
    return collected;
  }

  async function listAllForLevel(level, params = {}) {
    const path = LIST_ENDPOINT_BY_LEVEL[level];
    if (!path) return [];

    if (!LEVELS_WITH_ACTIVE_FILTER.has(level)) {
      return listAll(path, params);
    }

    const [activeItems, inactiveItems] = await Promise.all([
      listAll(path, { ...params, is_active: true }),
      listAll(path, { ...params, is_active: false })
    ]);

    const merged = new Map();
    [...activeItems, ...inactiveItems].forEach((item) => {
      if (item?.id) {
        merged.set(item.id, item);
      }
    });
    return Array.from(merged.values());
  }

  async function loadRootFaculties() {
    setLoadingRoot(true);
    setError('');
    try {
      const facultyItems = await listAllForLevel('faculties');
      setFaculties(facultyItems.map((item) => normalizeNode('faculties', item)));
    } catch (err) {
      const message = formatApiError(err, 'Failed to load faculties');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setFaculties([]);
    } finally {
      setLoadingRoot(false);
    }
  }

  useEffect(() => {
    loadRootFaculties();
  }, []);

  function clearTreeState() {
    setChildCache(createEmptyChildCache());
    setExpandedKeys({});
    setLoadingKeys({});
  }

  async function refreshTree() {
    clearTreeState();
    await loadRootFaculties();
  }

  function nodeKey(level, id) {
    return `${level}:${id}`;
  }

  function getChildLevel(level) {
    return CHILD_LEVEL_BY_LEVEL[level] || null;
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

  async function ensureChildrenLoaded(parentLevel, parentNode) {
    const childLevel = getChildLevel(parentLevel);
    if (!childLevel) return;

    const parentId = parentNode.id;
    if (hasChildrenLoaded(childLevel, parentId)) return;

    const loadKey = nodeKey(childLevel, parentId);
    if (loadingKeys[loadKey]) return;

    setLoadingKeys((prev) => ({ ...prev, [loadKey]: true }));
    try {
      const filterKey = FILTER_BY_CHILD_LEVEL[childLevel];
      const params = filterKey ? { [filterKey]: parentId } : {};
      const childItems = await listAllForLevel(childLevel, params);
      const normalized = childItems.map((item) => normalizeNode(childLevel, item));
      setChildCache((prev) => ({
        ...prev,
        [childLevel]: {
          ...prev[childLevel],
          [parentId]: normalized
        }
      }));
    } catch (err) {
      const levelMeta = getLevelMeta(childLevel);
      const message = formatApiError(err, `Failed to load ${levelMeta.label.toLowerCase()}`);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoadingKeys((prev) => ({ ...prev, [loadKey]: false }));
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
        code: raw.branch_name || '',
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
        branch_name: values.code.trim() || null,
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

  const visibleFaculties = useMemo(() => faculties.filter((node) => matchesQuery(node, query)), [faculties, query]);

  function renderNode(level, node, depth) {
    const childLevel = getChildLevel(level);
    const expanded = Boolean(expandedKeys[nodeKey(level, node.id)]);
    const childLoadingKey = nodeKey(childLevel, node.id);
    const loadingChildren = childLevel ? Boolean(loadingKeys[childLoadingKey]) : false;
    const children = childLevel ? getCachedChildren(childLevel, node.id) : [];
    const filteredChildren = children.filter((item) => matchesQuery(item, query));
    const childrenLoaded = childLevel ? hasChildrenLoaded(childLevel, node.id) : false;
    const levelMeta = getLevelMeta(level);
    const childLevelMeta = getLevelMeta(childLevel || level);

    return (
      <div key={nodeKey(level, node.id)} className="border-b border-slate-200 dark:border-slate-800">
        <div
          className={`grid grid-cols-[minmax(0,1fr)_170px_130px_86px] items-center gap-3 px-2 py-3 text-sm ${
            childLevel ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900/60' : ''
          }`}
          onClick={childLevel ? () => toggleNode(level, node) : undefined}
          role={childLevel ? 'button' : undefined}
          tabIndex={childLevel ? 0 : undefined}
          onKeyDown={
            childLevel
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
            {childLevel ? (
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

        {childLevel ? (
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
                    Loading {childLevelMeta.label.toLowerCase()}...
                  </p>
                ) : null}

                {!loadingChildren && childrenLoaded && filteredChildren.length === 0 ? (
                  <p className="px-6 pb-3 text-xs text-slate-500">
                    No {childLevelMeta.label.toLowerCase()} found under this {singularizeLabel(levelMeta.label).toLowerCase()}.
                  </p>
                ) : null}

                {!loadingChildren && filteredChildren.map((childNode) => renderNode(childLevel, childNode, depth + 1))}
              </motion.div>
            ) : null}
          </AnimatePresence>
        ) : null}
      </div>
    );
  }

  const editLevelMeta = editNode ? getLevelMeta(editNode.level) : null;
  const editSingularLabel = editLevelMeta ? singularizeLabel(editLevelMeta.label) : 'Node';
  const editCodeLabel = editNode?.level === 'semesters' ? 'Semester Number' : editNode?.level === 'sections' ? 'Branch Name' : 'Code';
  const editCodeType = editNode?.level === 'semesters' ? 'number' : 'text';

  return (
    <div className="space-y-5 page-fade">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Academic Structure</h1>
          <p className="mt-1 text-lg text-slate-500 dark:text-slate-400">
            Drill down faculty to sections with lazy-loaded hierarchy.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary !rounded-2xl !px-4 !py-3" onClick={refreshTree}>
            Refresh
          </button>
          <button
            className="btn-primary !rounded-2xl !px-5 !py-3 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => navigate('/faculties')}
            disabled={!canCreateFaculty}
            title={!canCreateFaculty ? 'Only super admin can add from this panel' : 'Add New Faculty'}
          >
            <Plus size={18} /> Add New Faculty
          </button>
        </div>
      </div>

      <Card className="space-y-4">
        <label className="relative block max-w-xl">
          <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input !h-12 !rounded-2xl !pl-11"
            placeholder="Search loaded hierarchy..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>

        {loadingRoot ? <p className="text-sm text-slate-500">Loading faculties...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900">
          <div className="grid grid-cols-[minmax(0,1fr)_170px_130px_86px] items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600 dark:border-slate-800 dark:bg-slate-800/70 dark:text-slate-200">
            <span>Name</span>
            <span>Code</span>
            <span>Status</span>
            <span className="text-right">Actions</span>
          </div>

          {visibleFaculties.length === 0 && !loadingRoot ? (
            <div className="px-4 py-8 text-center text-sm text-slate-500">No records found.</div>
          ) : (
            <div>{visibleFaculties.map((node) => renderNode('faculties', node, 0))}</div>
          )}
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

          <label className="block space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{editCodeLabel}</span>
            <input
              className="input"
              type={editCodeType}
              value={editValues.code}
              onChange={(event) => setEditValues((prev) => ({ ...prev, code: event.target.value }))}
              placeholder={editNode?.level === 'semesters' ? '1 - 12' : `Enter ${editCodeLabel.toLowerCase()}`}
              required={editNode?.level !== 'sections'}
            />
          </label>

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

