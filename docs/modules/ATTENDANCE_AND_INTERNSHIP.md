# Attendance And Internship

## Purpose

This module manages attendance capture for academic delivery and clock-in or clock-out flows for internship sessions.

## Data Model

Entities:

- attendance_records
- internship_sessions

Key relationships:

- attendance references students, sections, and course delivery context
- internship sessions are tied to user activity windows and auto-logout rules

## APIs

Primary endpoints:

- `/attendance-records`
- `/attendance-records/mark`
- `/attendance-records/mark-bulk`
- `/attendance-records/internship/clock-in`
- `/attendance-records/internship/clock-out`
- `/attendance-records/internship/status`

## Workflow

1. teacher or admin resolves the target attendance scope
2. individual or bulk marks are submitted
3. internship users can start and end sessions
4. status endpoints expose current internship presence state

## Dependencies

- `backend/app/api/v1/endpoints/attendance_records.py`
- `backend/app/models/attendance_records.py`
- `backend/app/models/internship_session.py`
- course delivery and student modules
