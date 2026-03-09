# Timetable Module Specification (Shift-Based, Multi-User)

This is the updated CAPS-AI timetable specification for universities operating multiple daily academic shifts.

## 1. Scope

The module must support timetable planning and publishing across this hierarchy:
- Program
- Batch
- Semester
- Section
- Academic Year
- Shift

Every timetable is shift-bound and slot-bound. A section is assigned to one shift, and all timetable entries for that section must use only slots from that shift template.

## 2. Shift Model

Two standard shifts are supported by default:

### Shift 1: Morning Shift
- Shift ID: `shift_1`
- Timing window: `08:30` to `14:20`
- Includes protected lunch period.

### Shift 2: Late Shift
- Shift ID: `shift_2`
- Timing window: `11:20` to `16:50`
- Includes protected lunch period.

### Shift Rules
- Shift slot templates define all valid slot keys for each shift.
- Slot types include:
  - `lecture` (or editable academic slot)
  - `lunch` (non-editable, non-bookable)
- Lunch slot is always locked.
- No timetable entry can be created outside shift start/end boundaries.

## 3. Default Slot Templates

Institutional defaults (can be modified by admin configuration):

### `shift_1` (Morning: 08:30-14:20)

| Slot Key | Start | End | Type | Editable |
|---|---|---|---|---|
| `p1` | 08:30 | 09:20 | lecture | Yes |
| `p2` | 09:20 | 10:10 | lecture | Yes |
| `p3` | 10:10 | 11:00 | lecture | Yes |
| `p4` | 11:10 | 12:00 | lecture | Yes |
| `lunch` | 12:00 | 12:50 | lunch | No |
| `p5` | 12:50 | 13:40 | lecture | Yes |
| `p6` | 13:40 | 14:20 | lecture | Yes |

### `shift_2` (Late: 11:20-16:50)

| Slot Key | Start | End | Type | Editable |
|---|---|---|---|---|
| `p1` | 11:20 | 12:10 | lecture | Yes |
| `p2` | 12:10 | 12:50 | lecture | Yes |
| `lunch` | 12:50 | 13:40 | lunch | No |
| `p3` | 13:40 | 14:30 | lecture | Yes |
| `p4` | 14:30 | 15:20 | lecture | Yes |
| `p5` | 15:20 | 16:10 | lecture | Yes |
| `p6` | 16:10 | 16:50 | lecture | Yes |

## 4. Timetable Creation Flow

When creating a timetable, users must select in this order:
1. Program
2. Batch
3. Semester
4. Section
5. Academic Year
6. Shift

After Shift selection:
- System auto-generates the timetable grid using the selected shift template.
- Only valid shift slots are shown.
- Lunch slot is rendered as locked/non-editable.

## 5. Scheduling and Validation Rules

The system must globally enforce:
- `slot_key` must belong to selected shift template.
- Section assigned to `shift_1` cannot use `shift_2` slots and vice versa.
- No entry can overlap lunch slot.
- No entry can start before shift start or end after shift end.
- No duplicate allocation for same `day + slot + section`.
- Teacher and room conflict checks across all active timetables.
- Teacher may teach in both shifts only if time windows do not overlap.

If an invalid slot is used:
- Reject save/publish.
- Error: `Invalid slot for selected shift`.

If bounds are violated:
- Reject with boundary error.

## 6. Course Duration Dependency

Program-level duration rules:
- `durationYears` allowed range: `3` to `5`.
- `totalSemesters = durationYears * 2` (auto-generated).
- Duration edits update semester count.
- Duration edits are blocked if students are already enrolled in affected semesters.

Impact on timetable:
- Semester lists for timetable generation come from `totalSemesters`.
- Shift grid generation is independent of duration but applied to each generated semester context.

## 7. Data Model Requirements

### Program
```json
{
  "programId": "string",
  "programName": "string",
  "departmentId": "string",
  "durationYears": 4,
  "totalSemesters": 8
}
```

### Section (minimum shift fields)
```json
{
  "sectionId": "string",
  "programId": "string",
  "batchId": "string",
  "semesterId": "string",
  "academicYear": "2026-27",
  "shiftId": "shift_1"
}
```

### Timetable
```json
{
  "id": "string",
  "programId": "string",
  "batchId": "string",
  "semester": "Sem-1",
  "sectionId": "string",
  "academicYear": "2026-27",
  "shiftId": "shift_1",
  "slots": [],
  "entries": [],
  "status": "draft|published",
  "adminLocked": false
}
```

## 8. Administrative Configuration

Shift templates must be admin-configurable:
- Update slot start/end times.
- Add/remove editable lecture slots.
- Keep one locked lunch slot mandatory per shift.
- Maintain shift boundary consistency.
- Version templates so existing published timetables remain immutable.

Recommended controls:
- `effective_from` semester/academic year.
- Template versioning and audit logs.

## 9. Access Control

| Action | Super Admin | Department Admin | Teacher | Student |
|---|---|---|---|---|
| Configure shift templates | Yes | Optional (policy) | No | No |
| Create/Edit timetable | Yes | Yes | Yes (assigned section) | No |
| Publish timetable | Yes | Yes | Yes (assigned section) | No |
| Lock/Unlock timetable | Yes | Yes | No | No |
| View own timetable | Yes | Yes | Yes | Yes |

## 10. API Contract (Current + Required)

Current endpoints:
- `GET /api/v1/timetables/shifts`
- `POST /api/v1/timetables/generate-grid`
- `GET /api/v1/timetables/lookups`
- `POST /api/v1/timetables/`
- `PUT /api/v1/timetables/{timetable_id}`
- `POST /api/v1/timetables/{timetable_id}/publish`
- `POST /api/v1/timetables/{timetable_id}/lock`
- `GET /api/v1/timetables/my`

Required payload fields for create/update flows:
- `programId`, `batchId`, `semester`, `sectionId`, `academicYear`, `shiftId`
- `entries[].slot_key` must be from selected shift template.

## 11. UX Requirements

For timetable creators:
- Show shift selector before grid.
- Render slot timings in row/column headers.
- Render lunch row/cell as locked badge (`Lunch - Locked`).
- On invalid slot selection, show immediate inline error.

For students/teachers:
- Timetable view must display shift label and shift time range.
- Slots must show start and end time clearly.

## 12. Error Messages

- `Course duration must be at least 3 years.`
- `Course duration cannot exceed 5 years.`
- `Invalid slot for selected shift.`
- `Lunch slot cannot be edited.`
- `Section shift mismatch: selected slot does not belong to section shift.`
- `Session is outside shift time boundaries.`
- `Cannot modify duration because students are already enrolled in existing semesters.`

## 13. Acceptance Checklist

- Shift is mandatory when creating timetable.
- Grid generation changes correctly by selected shift.
- Lunch is present and locked in both shifts.
- Slot-level validation rejects cross-shift entries.
- Section-shift binding is enforced.
- Teacher conflict validation works across both shifts.
- Student and teacher views match section shift template.
- Admin can update shift templates with version control.
