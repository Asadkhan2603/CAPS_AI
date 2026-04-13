const accessByAdminType = {
  super_admin: {
    canGovernance: true,
    canSystem: true,
    canRbac: true,
    canAuditLogs: true,
    canUsers: true,
    canOnboarding: true,
    canAcademicStructure: true,
    canObservability: true,
  },
  admin: {
    canGovernance: true,
    canSystem: true,
    canRbac: false,
    canAuditLogs: true,
    canUsers: true,
    canOnboarding: true,
    canAcademicStructure: true,
    canObservability: true,
  },
  academic_admin: {
    canGovernance: false,
    canSystem: false,
    canRbac: false,
    canAuditLogs: false,
    canUsers: false,
    canOnboarding: true,
    canAcademicStructure: true,
    canObservability: false,
  },
  compliance_admin: {
    canGovernance: false,
    canSystem: true,
    canRbac: false,
    canAuditLogs: true,
    canUsers: false,
    canOnboarding: false,
    canAcademicStructure: false,
    canObservability: true,
  },
};

const quickActionsByAdminType = {
  super_admin: [
    { to: '/admin/governance', label: 'Governance', description: 'Approve risky admin actions' },
    { to: '/admin/rbac', label: 'RBAC', description: 'Manage roles and permissions' },
    { to: '/audit-logs', label: 'Audit Logs', description: 'Review compliance events' },
    { to: '/admin/system', label: 'System Health', description: 'Inspect runtime status' },
  ],
  admin: [
    { to: '/admin/governance', label: 'Governance', description: 'Review pending approvals' },
    { to: '/users', label: 'Users', description: 'Manage administrative accounts' },
    { to: '/audit-logs', label: 'Audit Logs', description: 'Open the compliance trail' },
    { to: '/admin/system', label: 'System Health', description: 'Monitor platform health' },
  ],
  academic_admin: [
    { to: '/admin/onboarding', label: 'Onboarding', description: 'Continue academic setup' },
    { to: '/students', label: 'Students', description: 'Open student operations' },
    { to: '/academic-structure', label: 'Academic Structure', description: 'Manage the academic tree' },
    { to: '/admin/analytics', label: 'Analytics', description: 'Review platform metrics' },
  ],
  compliance_admin: [
    { to: '/admin/system', label: 'System Health', description: 'Track runtime incidents' },
    { to: '/admin/observability', label: 'Observability', description: 'Review request pressure' },
    { to: '/audit-logs', label: 'Audit Logs', description: 'Inspect audit activity' },
    { to: '/admin/analytics', label: 'Analytics', description: 'Check platform indicators' },
  ],
};

const summaryFallbackCards = [
  {
    key: 'total_users',
    label: 'Total Users',
    helper: 'Platform accounts in scope',
    getValue: ({ summary }) => summary.total_users ?? 0,
    variant: 'info',
  },
  {
    key: 'active_students',
    label: 'Active Students',
    helper: 'Currently active student base',
    getValue: ({ summary }) => summary.active_students ?? 0,
    variant: 'success',
  },
  {
    key: 'assignments_total',
    label: 'Assignments',
    helper: 'Assignments currently tracked',
    getValue: ({ summary }) => summary.assignments_total ?? 0,
    variant: 'default',
  },
  {
    key: 'active_clubs',
    label: 'Clubs',
    helper: 'Active clubs in the platform',
    getValue: ({ summary }) => summary.active_clubs ?? 0,
    variant: 'default',
  },
];

function getDbVariant(status) {
  const normalized = String(status || '').toLowerCase();
  if (!normalized || normalized === '-') {
    return 'default';
  }
  if (['ok', 'healthy', 'up', 'connected'].includes(normalized)) {
    return 'success';
  }
  return 'danger';
}

export function getAdminDashboardAccess(adminType = 'admin') {
  return accessByAdminType[adminType] || accessByAdminType.admin;
}

export function getAdminDashboardQuickActions(adminType = 'admin') {
  return quickActionsByAdminType[adminType] || quickActionsByAdminType.admin;
}

export function getAdminDashboardCriticalCards({
  summary = {},
  system = null,
  governance = null,
  access = {},
}) {
  const cards = [];
  const usedKeys = new Set();

  function addCard(card) {
    if (!card || usedKeys.has(card.key)) {
      return;
    }
    usedKeys.add(card.key);
    cards.push(card);
  }

  if (access.canGovernance) {
    addCard({
      key: 'pending_reviews',
      label: 'Pending Reviews',
      value: governance?.pending_reviews ?? 0,
      helper: 'Approval requests waiting now',
      variant: (governance?.pending_reviews ?? 0) > 0 ? 'warning' : 'success',
    });
    addCard({
      key: 'locked_accounts',
      label: 'Locked Accounts',
      value: governance?.locked_accounts ?? 0,
      helper: 'Accounts needing admin attention',
      variant: (governance?.locked_accounts ?? 0) > 0 ? 'danger' : 'default',
    });
    addCard({
      key: 'login_anomalies_24h',
      label: 'Login Anomalies (24h)',
      value: governance?.login_anomalies_24h ?? 0,
      helper: 'Suspicious sign-in activity',
      variant: (governance?.login_anomalies_24h ?? 0) > 0 ? 'warning' : 'default',
    });
  }

  if (access.canSystem) {
    const alertCount = system?.alert_count ?? system?.alerts?.length ?? 0;
    addCard({
      key: 'active_alerts',
      label: 'Active Alerts',
      value: alertCount,
      helper: 'Current operational issues',
      variant: alertCount > 0 ? 'danger' : 'success',
    });
    addCard({
      key: 'db_status',
      label: 'DB Status',
      value: system?.db_status || '-',
      helper: 'Primary data store health',
      variant: getDbVariant(system?.db_status),
    });
  }

  summaryFallbackCards.forEach((card) => {
    if (cards.length >= 4) {
      return;
    }
    addCard({
      key: card.key,
      label: card.label,
      value: card.getValue({ summary, system, governance }),
      helper: card.helper,
      variant: card.variant,
    });
  });

  return cards.slice(0, 4);
}
