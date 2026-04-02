import { useEffect, useState } from 'react';
import {
  BookOpen,
  Building2,
  CalendarDays,
  GraduationCap,
  Layers3,
  School,
  Users
} from 'lucide-react';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

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

const CHILD_PAGE_SIZE = 50;

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

function createEmptyChildPageState() {
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

export function singularizeLabel(label) {
  return label.endsWith('s') ? label.slice(0, -1) : label;
}

function normalizeNode(level, item) {
  if (level === 'universities') {
    return {
      id: item.id,
      level,
      name: item.university_name,
      code: item.public_id || item.university_id || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  if (level === 'semesters') {
    return {
      id: item.id,
      level,
      name: item.label,
      code: item.public_id || `S${item.semester_number}`,
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  if (level === 'sections') {
    return {
      id: item.id,
      level,
      name: item.name,
      code: item.public_id || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  if (level === 'groups') {
    return {
      id: item.id,
      level,
      name: item.name,
      code: item.public_id || item.code || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
      raw: item
    };
  }
  return {
    id: item.id,
    level,
    name: item.name,
    code: item.public_id || item.code || '-',
    status: item.is_active === false ? 'INACTIVE' : 'ACTIVE',
    raw: item
  };
}

export function matchesQuery(node, q) {
  const text = q.trim().toLowerCase();
  if (!text) return true;
  return [node.name, node.code, node.status].some((value) =>
    String(value || '')
      .toLowerCase()
      .includes(text)
  );
}

export function getLevelMeta(level) {
  return LEVELS.find((item) => item.key === level) || LEVELS[0];
}

export function getChildLevels(level) {
  return CHILD_LEVELS_BY_LEVEL[level] || [];
}

export function nodeKey(level, id) {
  return `${level}:${id}`;
}

export function getChildLevelLabel(level) {
  const childLevels = getChildLevels(level);
  if (!childLevels.length) return '';
  return childLevels.map((childLevel) => getLevelMeta(childLevel).label.toLowerCase()).join(' or ');
}

export function useAcademicStructureTree({ pushToast }) {
  const [rootNodes, setRootNodes] = useState([]);
  const [childCache, setChildCache] = useState(() => createEmptyChildCache());
  const [childPageState, setChildPageState] = useState(() => createEmptyChildPageState());
  const [expandedKeys, setExpandedKeys] = useState({});
  const [loadingKeys, setLoadingKeys] = useState({});
  const [loadingRoot, setLoadingRoot] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [rootSkip, setRootSkip] = useState(0);
  const [rootLimit, setRootLimit] = useState(50);

  async function fetchLevelPage(level, params = {}, cursorState = null) {
    const path = LIST_ENDPOINT_BY_LEVEL[level];
    if (!path) {
      return { items: [], nextCursorState: cursorState, hasMore: false };
    }

    if (!LEVELS_WITH_ACTIVE_FILTER.has(level)) {
      const skip = cursorState?.skip ?? 0;
      const response = await apiClient.get(path, {
        params: { ...params, skip, limit: CHILD_PAGE_SIZE }
      });
      const items = Array.isArray(response.data) ? response.data : [];
      return {
        items,
        nextCursorState: {
          skip: skip + items.length
        },
        hasMore: items.length === CHILD_PAGE_SIZE
      };
    }

    const activeSkip = cursorState?.activeSkip ?? 0;
    const inactiveSkip = cursorState?.inactiveSkip ?? 0;
    const [activeResponse, inactiveResponse] = await Promise.all([
      apiClient.get(path, {
        params: { ...params, is_active: true, skip: activeSkip, limit: CHILD_PAGE_SIZE }
      }),
      apiClient.get(path, {
        params: { ...params, is_active: false, skip: inactiveSkip, limit: CHILD_PAGE_SIZE }
      })
    ]);
    const activeItems = Array.isArray(activeResponse.data) ? activeResponse.data : [];
    const inactiveItems = Array.isArray(inactiveResponse.data) ? inactiveResponse.data : [];
    const merged = new Map();
    [...activeItems, ...inactiveItems].forEach((item) => {
      if (item?.id) {
        merged.set(item.id, item);
      }
    });
    return {
      items: Array.from(merged.values()),
      nextCursorState: {
        activeSkip: activeSkip + activeItems.length,
        inactiveSkip: inactiveSkip + inactiveItems.length
      },
      hasMore: activeItems.length === CHILD_PAGE_SIZE || inactiveItems.length === CHILD_PAGE_SIZE
    };
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
    setChildPageState(createEmptyChildPageState());
    setExpandedKeys({});
    setLoadingKeys({});
  }

  async function refreshTree() {
    clearTreeState();
    await loadRootUniversities();
  }

  function getCachedChildren(level, parentId) {
    if (!level || !parentId) return [];
    return childCache[level]?.[parentId] || [];
  }

  function hasChildrenLoaded(level, parentId) {
    if (!level || !parentId) return false;
    return Object.prototype.hasOwnProperty.call(childCache[level] || {}, parentId);
  }

  function getChildCursorState(level, parentId) {
    return childPageState[level]?.[parentId] || null;
  }

  function hasMoreChildren(level, parentId) {
    return Boolean(getChildCursorState(level, parentId)?.hasMore);
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

  async function ensureChildrenLoaded(parentLevel, parentNode, options = {}) {
    const childLevels = getChildLevels(parentLevel);
    if (!childLevels.length) return;
    const parentId = parentNode.id;
    const append = Boolean(options.append);
    const pendingLevels = childLevels.filter((childLevel) => {
      const loadKey = nodeKey(childLevel, parentId);
      if (loadingKeys[loadKey]) return false;
      if (append) {
        return hasMoreChildren(childLevel, parentId);
      }
      return !hasChildrenLoaded(childLevel, parentId);
    });
    if (!pendingLevels.length) return;

    setLoadingKeys((prev) => ({
      ...prev,
      ...Object.fromEntries(pendingLevels.map((childLevel) => [nodeKey(childLevel, parentId), true]))
    }));

    try {
      const results = await Promise.allSettled(
        pendingLevels.map(async (childLevel) => {
          const page = await fetchLevelPage(
            childLevel,
            getChildParams(parentLevel, childLevel, parentId),
            getChildCursorState(childLevel, parentId)
          );
          return {
            childLevel,
            normalized: normalizeChildItems(parentLevel, childLevel, page.items),
            nextCursorState: page.nextCursorState,
            hasMore: page.hasMore
          };
        })
      );

      setChildCache((prev) => {
        const next = { ...prev };
        results.forEach((result) => {
          if (result.status !== 'fulfilled') return;
          const { childLevel, normalized } = result.value;
          const existing = append ? next[childLevel]?.[parentId] || [] : [];
          const merged = new Map(existing.map((item) => [item.id, item]));
          normalized.forEach((item) => {
            merged.set(item.id, item);
          });
          next[childLevel] = {
            ...next[childLevel],
            [parentId]: Array.from(merged.values())
          };
        });
        return next;
      });

      setChildPageState((prev) => {
        const next = { ...prev };
        results.forEach((result) => {
          if (result.status !== 'fulfilled') return;
          const { childLevel, nextCursorState, hasMore } = result.value;
          next[childLevel] = {
            ...next[childLevel],
            [parentId]: {
              ...(nextCursorState || {}),
              hasMore
            }
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

  async function loadMoreChildren(level, node) {
    await ensureChildrenLoaded(level, node, { append: true });
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

  return {
    error,
    expandedKeys,
    getCachedChildren,
    hasChildrenLoaded,
    hasMoreChildren,
    loadMoreChildren,
    loadingKeys,
    loadingRoot,
    query,
    refreshTree,
    rootLimit,
    rootNodes,
    rootSkip,
    setQuery,
    setRootLimit,
    setRootSkip,
    toggleNode
  };
}
