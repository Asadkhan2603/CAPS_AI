const GROUP_ORDER = ['Academic structure', 'Communication', 'Student work', 'Clubs', 'Legacy'];

const COLLECTION_META = {
  departments: {
    label: 'Departments',
    group: 'Academic structure',
    description: 'Restore deleted academic departments and their structure anchors.',
    legacy: false,
    order: 0,
  },
  classes: {
    label: 'Classes',
    group: 'Academic structure',
    description: 'Recover deleted classes or sections used in teaching workflows.',
    legacy: false,
    order: 1,
  },
  notices: {
    label: 'Notices',
    group: 'Communication',
    description: 'Recover published notices removed from the communication stream.',
    legacy: false,
    order: 2,
  },
  notifications: {
    label: 'Notifications',
    group: 'Communication',
    description: 'Restore targeted notifications sent to users or groups.',
    legacy: false,
    order: 3,
  },
  assignments: {
    label: 'Assignments',
    group: 'Student work',
    description: 'Recover assignment records removed from coursework management.',
    legacy: false,
    order: 4,
  },
  submissions: {
    label: 'Submissions',
    group: 'Student work',
    description: 'Restore student submissions removed from review flows.',
    legacy: false,
    order: 5,
  },
  evaluations: {
    label: 'Evaluations',
    group: 'Student work',
    description: 'Recover evaluation outcomes or grading records.',
    legacy: false,
    order: 6,
  },
  review_tickets: {
    label: 'Review Tickets',
    group: 'Student work',
    description: 'Restore review tickets tied to academic moderation workflows.',
    legacy: false,
    order: 7,
  },
  clubs: {
    label: 'Clubs',
    group: 'Clubs',
    description: 'Recover deleted clubs and their workspace shells.',
    legacy: false,
    order: 8,
  },
  club_events: {
    label: 'Club Events',
    group: 'Clubs',
    description: 'Restore deleted club events and registration context.',
    legacy: false,
    order: 9,
  },
  branches: {
    label: 'Branches',
    group: 'Legacy',
    description: 'Legacy branch records kept for compatibility workflows.',
    legacy: true,
    order: 10,
  },
  courses: {
    label: 'Courses',
    group: 'Legacy',
    description: 'Legacy course records retained for older data models.',
    legacy: true,
    order: 11,
  },
  years: {
    label: 'Years',
    group: 'Legacy',
    description: 'Legacy academic year records retained for older flows.',
    legacy: true,
    order: 12,
  },
};

export function getRecoveryCollectionMeta(key) {
  const fallbackLabel = String(key || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  return COLLECTION_META[key] || {
    label: fallbackLabel,
    group: 'Other',
    description: 'Recovery collection',
    legacy: false,
    order: Number.MAX_SAFE_INTEGER,
  };
}

export function normalizeRecoveryCatalog(catalog = []) {
  const rows = Array.isArray(catalog) ? catalog : [];
  return rows
    .map((item) => {
      const meta = getRecoveryCollectionMeta(item.key);
      return {
        key: item.key,
        label: item.label || meta.label,
        group: item.group || meta.group,
        description: meta.description,
        legacy: item.legacy ?? meta.legacy,
        order: meta.order,
      };
    })
    .sort((left, right) => left.order - right.order || left.label.localeCompare(right.label));
}

export function groupRecoveryCatalog(catalog = []) {
  return GROUP_ORDER
    .map((group) => ({
      group,
      items: catalog.filter((item) => item.group === group),
    }))
    .filter((entry) => entry.items.length > 0);
}

export function getDefaultRecoveryCollection(catalog = [], preferredKey = 'notices') {
  if (catalog.some((item) => item.key === preferredKey)) {
    return preferredKey;
  }
  const firstActive = catalog.find((item) => item.legacy !== true);
  return firstActive?.key || catalog[0]?.key || preferredKey;
}

export function getRecoveryStatusVariant(statusLabel) {
  const normalized = String(statusLabel || '').trim().toLowerCase();
  if (normalized === 'active') return 'success';
  if (normalized === 'inactive' || normalized === 'archived') return 'warning';
  if (normalized === 'critical') return 'danger';
  return 'default';
}
