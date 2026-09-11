/**
 * KOHA-CIL Security Gateway — Role Definitions & RBAC Configuration
 *
 * Roles:
 *   HQ_OFFICER       — Full access to all subsidiaries
 *   SUBSIDIARY_OFFICER — Restricted to assigned subsidiary
 *   ADMIN            — Full access + admin operations
 */

const ROLES = {
  HQ_OFFICER: 'HQ_OFFICER',
  SUBSIDIARY_OFFICER: 'SUBSIDIARY_OFFICER',
  ADMIN: 'ADMIN',
};

const SUBSIDIARIES = ['ECL', 'BCCL', 'CCL', 'SECL', 'MCL'];

/**
 * Permissions matrix.
 * Each permission key maps to roles that may exercise it.
 */
const PERMISSIONS = {
  QUERY_ANY:         [ROLES.HQ_OFFICER, ROLES.ADMIN],
  QUERY_OWN:         [ROLES.HQ_OFFICER, ROLES.SUBSIDIARY_OFFICER, ROLES.ADMIN],
  INGEST:            [ROLES.HQ_OFFICER, ROLES.ADMIN],
  VIEW_CONFLICTS:    [ROLES.HQ_OFFICER, ROLES.SUBSIDIARY_OFFICER, ROLES.ADMIN],
  REVIEW_CONFLICTS:  [ROLES.HQ_OFFICER, ROLES.ADMIN],
  VIEW_AUDIT:        [ROLES.HQ_OFFICER, ROLES.SUBSIDIARY_OFFICER, ROLES.ADMIN],
  VIEW_DASHBOARD:    [ROLES.HQ_OFFICER, ROLES.SUBSIDIARY_OFFICER, ROLES.ADMIN],
};

/**
 * Check if a role has a given permission.
 * @param {string} role
 * @param {string} permission
 * @returns {boolean}
 */
function hasPermission(role, permission) {
  const allowed = PERMISSIONS[permission];
  if (!allowed) return false;
  return allowed.includes(role);
}

/**
 * Check if a user may access a given subsidiary's data.
 * HQ/ADMIN can access any subsidiary.
 * SUBSIDIARY_OFFICER can only access their own.
 *
 * @param {object} user - { role, subsidiary }
 * @param {string|null} requestedSubsidiary - subsidiary being requested (null = all)
 * @returns {boolean}
 */
function canAccessSubsidiary(user, requestedSubsidiary) {
  if (!requestedSubsidiary) {
    // Requesting all subsidiaries — only HQ/ADMIN allowed
    return [ROLES.HQ_OFFICER, ROLES.ADMIN].includes(user.role);
  }
  if ([ROLES.HQ_OFFICER, ROLES.ADMIN].includes(user.role)) {
    return true;
  }
  if (user.role === ROLES.SUBSIDIARY_OFFICER) {
    return user.subsidiary === requestedSubsidiary;
  }
  return false;
}

module.exports = { ROLES, SUBSIDIARIES, PERMISSIONS, hasPermission, canAccessSubsidiary };
