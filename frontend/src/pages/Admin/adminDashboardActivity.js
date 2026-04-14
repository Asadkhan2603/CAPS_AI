import { buildAuditLogsPath } from './adminWorkflowLinks';

const outcomeDefinitions = [
  {
    key: 'restore_completed',
    title: 'Restore completed',
    matches: (row) => String(row?.action || '').toLowerCase().includes('restore'),
    detail: (row) => `Latest restore on ${getEntityLabel(row)} by ${getActorLabel(row)}.`,
  },
  {
    key: 'access_change_recorded',
    title: 'Access change recorded',
    matches: (row) => {
      const action = String(row?.action || '').toLowerCase();
      const resourceType = String(row?.resource_type || '').toLowerCase();
      const entityType = String(row?.entity_type || '').toLowerCase();
      return (
        action.startsWith('rbac_')
        || action === 'status_update'
        || resourceType === 'admin_user'
        || resourceType === 'rbac_role'
        || entityType === 'admin_user'
        || entityType === 'rbac_role'
      );
    },
    detail: (row) => `${getActionLabel(row)} for ${getEntityLabel(row)} was recorded in the audit trail.`,
  },
  {
    key: 'governance_decision_logged',
    title: 'Governance decision logged',
    matches: (row) => {
      const action = String(row?.action || '').toLowerCase();
      const resourceType = String(row?.resource_type || '').toLowerCase();
      const entityType = String(row?.entity_type || '').toLowerCase();
      return (
        resourceType.includes('governance')
        || entityType.includes('governance')
        || action.includes('approve')
        || action.includes('reject')
        || action.includes('governance')
      );
    },
    detail: (row) => `${getActionLabel(row)} on ${getEntityLabel(row)} is ready for verification.`,
  },
  {
    key: 'session_activity_logged',
    title: 'Session activity logged',
    matches: (row) => {
      const resourceType = String(row?.resource_type || '').toLowerCase();
      const entityType = String(row?.entity_type || '').toLowerCase();
      return resourceType === 'user_session' || entityType === 'user_session';
    },
    detail: (row) => `${getEntityLabel(row)} session activity was captured for compliance review.`,
  },
];

function humanizeToken(value) {
  return String(value || '')
    .replace(/[._-]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getTimestampValue(value) {
  const timestamp = value ? new Date(value).getTime() : 0;
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function sortAuditRowsNewestFirst(rows = []) {
  return [...rows].sort(
    (left, right) => getTimestampValue(right?.created_at) - getTimestampValue(left?.created_at),
  );
}

export function getActionLabel(row = {}) {
  return row.action_label || humanizeToken(row.action || 'Activity');
}

export function getActorLabel(row = {}) {
  return row.actor_label || row.actor_user_id || 'Unknown actor';
}

export function getEntityLabel(row = {}) {
  return (
    row.entity_label
    || row.public_id
    || row.entity_id
    || humanizeToken(row.resource_type || row.entity_type || 'record')
  );
}

export function buildDashboardAuditLogPath(row = {}) {
  return buildAuditLogsPath({
    action: row.action || '',
    entity_type: row.entity_type || '',
    resource_type: row.resource_type || row.entity_type || '',
    actor_user_id: row.actor_user_id || '',
  });
}

export function mapDashboardActivityItems(rows = []) {
  return sortAuditRowsNewestFirst(rows).slice(0, 5).map((row, index) => ({
    id: row.id || row.public_id || `${row.action || 'activity'}-${index}`,
    actionLabel: getActionLabel(row),
    entityLabel: getEntityLabel(row),
    actorLabel: getActorLabel(row),
    timestampLabel: row.created_at ? new Date(row.created_at).toLocaleString() : 'Unknown time',
    to: buildDashboardAuditLogPath(row),
  }));
}

export function mapDashboardOutcomeItems(rows = []) {
  const sortedRows = sortAuditRowsNewestFirst(rows);
  const usedIds = new Set();

  return outcomeDefinitions.reduce((accumulator, definition) => {
    if (accumulator.length >= 3) {
      return accumulator;
    }

    const matchedRow = sortedRows.find((row) => {
      const rowId = row.id || row.public_id || `${row.action || 'activity'}-${row.created_at || ''}`;
      return !usedIds.has(rowId) && definition.matches(row);
    });

    if (!matchedRow) {
      return accumulator;
    }

    const rowId =
      matchedRow.id
      || matchedRow.public_id
      || `${matchedRow.action || definition.key}-${matchedRow.created_at || accumulator.length}`;
    usedIds.add(rowId);
    accumulator.push({
      id: `${definition.key}-${rowId}`,
      title: definition.title,
      detail: definition.detail(matchedRow),
      timestampLabel: matchedRow.created_at
        ? new Date(matchedRow.created_at).toLocaleString()
        : 'Unknown time',
      to: buildDashboardAuditLogPath(matchedRow),
    });
    return accumulator;
  }, []);
}

export function mapAcademicAdminDashboardClosure(overview = null) {
  if (!overview || typeof overview !== 'object') {
    return {
      activity: null,
      outcomes: null,
    };
  }

  const progress = overview.progress || {};
  const nextStep = overview.next_step || null;
  const steps = Array.isArray(overview.steps) ? overview.steps : [];
  const completedSteps = steps.filter((step) => step?.is_complete);
  const latestCompletedMilestone = completedSteps.at(-1) || null;
  const nextPath = nextStep?.action_path || '/admin/onboarding';

  return {
    activity: {
      progressPercent: progress.percent ?? 0,
      completedSteps: progress.completed_steps ?? 0,
      totalSteps: progress.total_steps ?? 0,
      nextStepLabel: nextStep?.label || 'Continue setup',
      nextStepDescription:
        nextStep?.description
        || 'Continue the guided academic setup to unlock more admin workflows.',
      ctaLabel: nextStep?.cta_label || 'Open Onboarding',
      ctaTo: '/admin/onboarding',
    },
    outcomes: {
      latestCompletedLabel: latestCompletedMilestone?.label || 'No completed milestone yet',
      latestCompletedDescription: latestCompletedMilestone
        ? latestCompletedMilestone.description || 'A completed onboarding milestone is ready for review.'
        : 'Your first completed milestone will appear here after the next onboarding action.',
      nextStepLabel: nextStep?.label || 'Continue onboarding',
      nextStepDescription:
        nextStep?.description || 'Use the guided setup flow to keep academic onboarding moving.',
      ctaLabel: nextStep?.cta_label || 'Open Onboarding',
      ctaTo: nextPath,
    },
  };
}
