export function buildAuditLogsPath(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return query ? `/audit-logs?${query}` : '/audit-logs';
}

export function buildGovernancePath(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return query ? `/admin/governance?${query}` : '/admin/governance';
}

export function buildRbacPath(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return query ? `/admin/rbac?${query}` : '/admin/rbac';
}

export function buildRecoveryAuditLogPath(collection) {
  return buildAuditLogsPath({
    action: 'restore',
    resource_type: collection,
  });
}

export function buildRbacAuditLogPath(context = {}) {
  const action = context.actionType || context.action_type || context.action || '';
  const entityType = context.entityType || context.entity_type || '';
  const resourceType = context.resourceType
    || context.resource_type
    || entityType
    || (String(action).startsWith('rbac_') ? 'rbac_role' : 'admin_user');

  return buildAuditLogsPath({
    resource_type: resourceType,
    entity_type: entityType,
    action,
    actor_user_id: context.actorUserId || context.actor_user_id || '',
  });
}

export function buildGovernanceReviewFollowUp(row = {}) {
  const reviewType = String(row.review_type || '').toLowerCase();
  const action = row.action || '';
  const entityType = row.entity_type || '';
  const auditFilters = {
    action,
    entity_type: entityType,
    resource_type: entityType,
  };

  if (reviewType === 'role_change') {
    return {
      primaryLabel: 'Open RBAC',
      primaryTo: buildRbacPath({ context: 'role_change' }),
      secondaryLabel: 'Open Audit Logs',
      secondaryTo: buildAuditLogsPath(auditFilters),
      helperText: 'Role-change reviews usually continue in RBAC before final audit verification.',
    };
  }

  return {
    primaryLabel: 'Open Audit Logs',
    primaryTo: buildAuditLogsPath(auditFilters),
    secondaryLabel: 'Open Governance',
    secondaryTo: buildGovernancePath({ status: row.status || '' }),
    helperText: 'Destructive-action reviews usually continue with audit verification after the decision.',
  };
}

export function buildGovernanceSessionFollowUp(row = {}) {
  return {
    primaryLabel: 'Open Audit Logs',
    primaryTo: buildAuditLogsPath({
      entity_type: 'user_session',
      resource_type: 'user_session',
    }),
    helperText: 'Use audit logs to verify device-session actions and related security follow-up.',
  };
}

export function buildRbacResultLinks(context = {}) {
  return {
    governanceTo: buildGovernancePath({ context: 'rbac_follow_up' }),
    auditTo: buildRbacAuditLogPath(context),
  };
}

export function buildGovernanceResultLinks(context = {}) {
  const reviewType = String(context.reviewType || '').toLowerCase();
  const auditFilters = {
    action: context.action || '',
    entity_type: context.entityType || '',
    resource_type: context.resourceType || context.entityType || '',
  };

  return {
    auditTo: buildAuditLogsPath(auditFilters),
    rbacTo: reviewType === 'role_change' ? buildRbacPath({ context: 'role_change' }) : buildRbacPath(),
  };
}
