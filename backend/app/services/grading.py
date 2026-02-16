def attendance_points(attendance_percent: int) -> int:
    if 95 <= attendance_percent <= 100:
        return 5
    if 90 <= attendance_percent <= 94:
        return 4
    if 85 <= attendance_percent <= 89:
        return 3
    if 80 <= attendance_percent <= 84:
        return 2
    if 70 <= attendance_percent <= 79:
        return 1
    return 0


def internal_total(
    attendance_percent: int, skill: float, behavior: float, report: float, viva: float
) -> float:
    return attendance_points(attendance_percent) + skill + behavior + report + viva


def grand_total(
    attendance_percent: int,
    skill: float,
    behavior: float,
    report: float,
    viva: float,
    final_exam: int,
) -> float:
    return internal_total(attendance_percent, skill, behavior, report, viva) + final_exam


def grade_from_total(total: float) -> str:
    if 90 <= total <= 100:
        return "A+"
    if 80 <= total < 90:
        return "A"
    if 70 <= total < 80:
        return "B"
    if 60 <= total < 70:
        return "C"
    return "Needs Improvement"
