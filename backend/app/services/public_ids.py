from __future__ import annotations

import re
from typing import Any, Mapping


_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")
_YEAR_RE = re.compile(r"(20\d{2})")


def _clean_token(value: Any, *, max_length: int | None = None) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    token = _NON_ALNUM_RE.sub("-", text).strip("-")
    if not token:
        return None
    if max_length is not None:
        token = token[:max_length].strip("-")
    return token or None


def _alnum_tail(value: Any, *, length: int = 4) -> str:
    text = re.sub(r"[^A-Za-z0-9]", "", str(value or "").upper())
    if not text:
        return "NA"
    return text[-length:]


def _persisted_tail(value: Any, *, length: int = 4) -> str | None:
    tail = _alnum_tail(value, length=length)
    return None if tail == "NA" else tail


def _acronym(value: Any, *, max_length: int = 8) -> str | None:
    words = re.findall(r"[A-Za-z0-9]+", str(value or ""))
    if not words:
        return None
    stop_words = {"OF", "AND", "THE", "IN", "FOR", "TO", "ON"}
    letters = [word[0].upper() for word in words if word.upper() not in stop_words]
    if letters:
        return "".join(letters)[:max_length]
    return _clean_token(words[0], max_length=max_length)


def _prefixed(prefix: str, token: Any, *, max_length: int = 24) -> str | None:
    normalized_prefix = _clean_token(prefix, max_length=8)
    normalized_token = _clean_token(token, max_length=max_length)
    if not normalized_prefix or not normalized_token:
        return None
    if normalized_token == normalized_prefix or normalized_token.startswith(f"{normalized_prefix}-"):
        return normalized_token
    return f"{normalized_prefix}-{normalized_token}"


def _first_token(*values: Any, max_length: int = 24) -> str | None:
    for value in values:
        token = _clean_token(value, max_length=max_length)
        if token:
            return token
    return None


def _first_year(*values: Any) -> str | None:
    for value in values:
        match = _YEAR_RE.search(str(value or ""))
        if match:
            return match.group(1)
    return None


def _section_token(document: Mapping[str, Any]) -> str | None:
    explicit = _first_token(
        document.get("section_code"),
        document.get("code"),
        max_length=8,
    )
    if explicit:
        return explicit
    name = str(document.get("name") or document.get("section_name") or "").strip()
    if not name:
        return None
    match = re.search(r"(section|class)\s+([A-Za-z0-9-]+)$", name, flags=re.IGNORECASE)
    if match:
        return _clean_token(match.group(2), max_length=8)
    return _acronym(name, max_length=6)


def build_public_id(
    kind: str,
    document: Mapping[str, Any],
    *,
    prefer_existing: bool = True,
) -> str | None:
    existing = _clean_token(document.get("public_id"), max_length=32)
    if prefer_existing and existing:
        return existing

    if kind == "university":
        return _first_token(
            document.get("university_id"),
            document.get("university_code"),
            _acronym(document.get("university_name"), max_length=10),
            max_length=16,
        )
    if kind == "faculty":
        return _prefixed(
            "FAC",
            _first_token(document.get("faculty_code"), document.get("code"), _acronym(document.get("faculty_name"), max_length=10)),
        )
    if kind == "department":
        return _prefixed(
            "DPT",
            _first_token(document.get("department_code"), document.get("code"), _acronym(document.get("department_name"), max_length=10)),
        )
    if kind == "program":
        return _prefixed(
            "PRG",
            _first_token(document.get("program_code"), document.get("code"), _acronym(document.get("program_name"), max_length=14)),
            max_length=28,
        )
    if kind == "specialization":
        return _prefixed(
            "SPC",
            _first_token(document.get("specialization_code"), document.get("code"), _acronym(document.get("specialization_name"), max_length=10)),
        )
    if kind == "batch":
        return _prefixed(
            "BAT",
            _first_year(document.get("start_year"), document.get("code"), document.get("name"))
            or _first_token(document.get("code"), max_length=12)
            or _alnum_tail(document.get("_id") or document.get("id")),
        )
    if kind == "semester":
        number = document.get("semester_number")
        if isinstance(number, int):
            return f"SEM-{number:02d}"
        token = _first_token(document.get("label"), max_length=12) or _alnum_tail(document.get("_id") or document.get("id"))
        return _prefixed("SEM", token)
    if kind == "section":
        return _prefixed("SEC", _section_token(document) or _alnum_tail(document.get("_id") or document.get("id")))
    if kind == "group":
        return _prefixed("GRP", _first_token(document.get("code"), _acronym(document.get("name"), max_length=8), max_length=10) or _alnum_tail(document.get("_id") or document.get("id")))
    if kind == "subject":
        return _prefixed("SUB", _first_token(document.get("code"), _acronym(document.get("name"), max_length=10), max_length=14) or _alnum_tail(document.get("_id") or document.get("id")))
    if kind == "student":
        roll_token = _clean_token(document.get("roll_number"), max_length=16)
        if roll_token:
            return _prefixed("STU", roll_token)
        year = _first_year(document.get("batch_name"), document.get("academic_year"))
        suffix = _alnum_tail(document.get("_id") or document.get("id"), length=5)
        return f"STU-{year}-{suffix}" if year else f"STU-{suffix}"
    if kind == "assignment":
        token = _first_token(document.get("subject_code"), _acronym(document.get("title"), max_length=10), max_length=12)
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3 if token else 5)
        if not tail:
            return None
        return _prefixed("ASG", f"{token}-{tail}" if token else tail)
    if kind == "submission":
        student = _persisted_tail(document.get("student_user_id"), length=4) or "USER"
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3)
        return f"SBM-{student}-{tail}" if tail else None
    if kind == "evaluation":
        submission = _persisted_tail(document.get("submission_id"), length=4) or "SUBM"
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3)
        return f"EVL-{submission}-{tail}" if tail else None
    if kind == "course_offering":
        token = _first_token(document.get("subject_code"), document.get("academic_year"), max_length=12)
        return _prefixed("OFF", token or _alnum_tail(document.get("_id") or document.get("id"), length=5))
    if kind == "class_slot":
        day = _clean_token(str(document.get("day") or "")[:3], max_length=3) or "SLT"
        time_token = re.sub(r"[^0-9]", "", str(document.get("start_time") or ""))[:4] or _alnum_tail(document.get("_id") or document.get("id"), length=4)
        return f"SLT-{day}-{time_token}"
    if kind == "club":
        return _prefixed("CLB", _first_token(document.get("slug"), _acronym(document.get("name"), max_length=10), max_length=14) or _alnum_tail(document.get("_id") or document.get("id")))
    if kind == "club_member":
        club = _persisted_tail(document.get("club_id"), length=3) or "CLB"
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3)
        return f"MBR-{club}-{tail}" if tail else None
    if kind == "club_application":
        club = _persisted_tail(document.get("club_id"), length=3) or "CLB"
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3)
        return f"APP-{club}-{tail}" if tail else None
    if kind == "club_event":
        base = _first_token(_acronym(document.get("title"), max_length=8), max_length=8) or _alnum_tail(document.get("club_id"), length=4)
        date_token = _first_year(document.get("event_date")) or _alnum_tail(document.get("_id") or document.get("id"), length=3)
        return f"EVT-{base}-{date_token}"
    if kind == "notification":
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=4)
        return f"NTF-{tail}" if tail else None
    if kind == "attendance_record":
        student = _persisted_tail(document.get("student_id"), length=3) or "STU"
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3)
        return f"ATT-{student}-{tail}" if tail else None
    if kind == "event_registration":
        event = _persisted_tail(document.get("event_id"), length=3) or "EVT"
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=3)
        return f"REG-{event}-{tail}" if tail else None
    if kind == "review_ticket":
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=4)
        return f"RVT-{tail}" if tail else None
    if kind == "audit_log":
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=4)
        return f"ADT-{tail}" if tail else None
    if kind == "admin_action_review":
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=4)
        return f"APR-{tail}" if tail else None
    if kind == "user_session":
        tail = _persisted_tail(document.get("_id") or document.get("id"), length=4)
        return f"SES-{tail}" if tail else None
    return _clean_token(document.get("code"), max_length=20) or _alnum_tail(document.get("_id") or document.get("id"), length=6)


def persist_public_id(
    document: dict[str, Any],
    *,
    kind: str,
    prefer_existing: bool = False,
) -> dict[str, Any]:
    public_id = build_public_id(kind, document, prefer_existing=prefer_existing)
    if public_id:
        document["public_id"] = public_id
    return document


def persist_public_id_update(
    current: Mapping[str, Any],
    update_data: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(current)
    merged.update(update_data)
    public_id = build_public_id(kind, merged, prefer_existing=False)
    if public_id:
        update_data["public_id"] = public_id
    return update_data


def build_user_label(user_id: Any, *, full_name: Any = None, email: Any = None) -> str | None:
    name = str(full_name or "").strip()
    mail = str(email or "").strip()
    if name and mail:
        return f"{name} ({mail})"
    if name:
        return name
    if mail:
        return mail
    token = _alnum_tail(user_id, length=4)
    return None if token == "NA" else f"User {token}"


def build_entity_label(entity_type: Any, entity_id: Any, *, entity_name: Any = None) -> str | None:
    name = str(entity_name or "").strip()
    if name:
        return name
    type_label = str(entity_type or "entity").replace("_", " ").strip().title() or "Entity"
    token = _alnum_tail(entity_id, length=4)
    return f"{type_label} {token}" if token != "NA" else type_label


def build_display_label(kind: str, document: Mapping[str, Any], *, public_id: str | None = None, display_name: str | None = None) -> str | None:
    name = str(display_name or "").strip()
    if not name:
        for field_name in (
            "university_name",
            "faculty_name",
            "department_name",
            "program_name",
            "specialization_name",
            "title",
            "label",
            "name",
            "full_name",
            "action",
        ):
            candidate = str(document.get(field_name) or "").strip()
            if candidate:
                name = candidate
                break
    if name and public_id:
        return f"{name} ({public_id})"
    return name or public_id


def apply_public_identity(
    payload: dict[str, Any],
    *,
    kind: str,
    document: Mapping[str, Any],
    display_name: str | None = None,
) -> dict[str, Any]:
    public_id = build_public_id(kind, document)
    if public_id:
        payload["public_id"] = public_id
    payload["display_label"] = build_display_label(kind, document, public_id=public_id, display_name=display_name)
    return payload
