from __future__ import annotations

# Enterprise-ready permission registry.
# Each permission can be mapped by:
# - roles
# - admin_types (for role=admin)
# - teacher_extensions (for role=teacher)
# - student_extensions (for role=student)
PERMISSION_REGISTRY: dict[str, dict[str, set[str]]] = {
    # Existing permissions used by endpoints.
    "users.read": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin"},
    },
    "users.update": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin"},
    },
    "analytics.read": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "academic_admin", "compliance_admin"},
    },
    "audit.read": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "compliance_admin"},
    },
    "system.read": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "compliance_admin"},
    },
    "announcements.publish": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
        "teacher_extensions": {"year_head", "class_coordinator", "club_coordinator"},
    },
    "courses.manage": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "academic_admin"},
    },
    "departments.manage": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "academic_admin"},
    },
    "sections.manage": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "academic_admin"},
    },
    "clubs.manage": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
        "teacher_extensions": {"club_coordinator"},
    },
    # New Phase-1 permission keys requested.
    "club:create": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin"},
    },
    "club:update": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
    },
    "academic:manage": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "academic_admin"},
    },
    "admin:analytics": {
        "roles": {"admin"},
        "admin_types": {"super_admin", "admin", "academic_admin", "compliance_admin"},
    },
    "communication:publish": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
        "teacher_extensions": {"year_head", "class_coordinator", "club_coordinator"},
    },
}
