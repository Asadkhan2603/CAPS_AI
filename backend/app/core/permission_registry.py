from __future__ import annotations


def _admin_rule(*admin_types: str) -> dict[str, set[str]]:
    return {
        "roles": {"admin"},
        "admin_types": set(admin_types),
    }


# Enterprise-ready permission registry.
# Each permission can be mapped by:
# - roles
# - admin_types (for role=admin)
# - teacher_extensions (for role=teacher)
# - student_extensions (for role=student)
PERMISSION_REGISTRY: dict[str, dict[str, set[str]]] = {
    # Existing permissions used by endpoints.
    "users.read": _admin_rule("super_admin", "admin"),
    "users.update": _admin_rule("super_admin"),
    "analytics.read": _admin_rule("super_admin", "admin", "academic_admin", "compliance_admin"),
    "audit.read": _admin_rule("super_admin", "admin", "compliance_admin"),
    "system.read": _admin_rule("super_admin", "admin", "compliance_admin"),
    "announcements.publish": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
        "teacher_extensions": {"year_head", "class_coordinator", "club_coordinator"},
    },
    "faculties.manage": _admin_rule("super_admin", "admin", "academic_admin"),
    "departments.manage": _admin_rule("super_admin", "admin", "academic_admin"),
    "programs.manage": _admin_rule("super_admin", "admin", "academic_admin", "department_admin"),
    "specializations.manage": _admin_rule("super_admin", "admin", "academic_admin", "department_admin"),
    "batches.manage": _admin_rule("super_admin", "admin", "academic_admin", "department_admin"),
    "semesters.manage": _admin_rule("super_admin", "admin", "academic_admin", "department_admin"),
    "sections.manage": _admin_rule("super_admin", "admin", "academic_admin", "department_admin"),
    "clubs.manage": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
        "teacher_extensions": {"club_coordinator"},
    },
    # New Phase-1 permission keys requested.
    "club:create": _admin_rule("super_admin", "admin"),
    "club:update": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
    },
    "academic:manage": _admin_rule("super_admin"),
    "admin:analytics": _admin_rule("super_admin", "admin", "academic_admin", "compliance_admin"),
    "communication:publish": {
        "roles": {"admin", "teacher"},
        "admin_types": {"super_admin", "admin"},
        "teacher_extensions": {"year_head", "class_coordinator", "club_coordinator"},
    },
}


ACADEMIC_ROUTE_PERMISSION_MATRIX: dict[str, dict[str, str]] = {
    "/faculties": {
        "GET": "role:admin|teacher",
        "POST": "faculties.manage",
        "PUT": "faculties.manage",
        "DELETE": "faculties.manage",
    },
    "/departments": {
        "GET": "role:admin|teacher",
        "POST": "departments.manage",
        "PUT": "departments.manage",
        "DELETE": "departments.manage",
    },
    "/programs": {
        "GET": "role:admin|teacher",
        "POST": "programs.manage",
        "PUT": "programs.manage",
        "DELETE": "programs.manage",
    },
    "/specializations": {
        "GET": "role:admin|teacher",
        "POST": "specializations.manage",
        "PUT": "specializations.manage",
        "DELETE": "specializations.manage",
    },
    "/batches": {
        "GET": "role:admin|teacher",
        "POST": "batches.manage",
        "PUT": "batches.manage",
        "DELETE": "batches.manage",
    },
    "/semesters": {
        "GET": "role:admin|teacher",
        "POST": "semesters.manage",
        "PUT": "semesters.manage",
        "DELETE": "semesters.manage",
    },
    "/sections": {
        "GET": "role:admin|teacher",
        "POST": "sections.manage",
        "PUT": "sections.manage",
        "DELETE": "sections.manage",
    },
}
