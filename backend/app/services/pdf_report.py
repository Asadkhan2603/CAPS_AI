from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_evaluation_report(data: Dict[str, Any]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 48
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(48, y, "CAPS AI Evaluation Report")

    y -= 24
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, y, f"Generated At: {datetime.now(timezone.utc).isoformat()}")

    lines = [
        f"Student User ID: {data.get('student_user_id', '-')}",
        f"Submission ID: {data.get('submission_id', '-')}",
        f"Teacher User ID: {data.get('teacher_user_id', '-')}",
        f"Attendance %: {data.get('attendance_percent', '-')}",
        f"Skill: {data.get('skill', '-')}",
        f"Behavior: {data.get('behavior', '-')}",
        f"Report: {data.get('report', '-')}",
        f"Viva: {data.get('viva', '-')}",
        f"Final Exam: {data.get('final_exam', '-')}",
        f"Internal Total: {data.get('internal_total', '-')}",
        f"Grand Total: {data.get('grand_total', '-')}",
        f"Grade: {data.get('grade', '-')}",
    ]

    y -= 26
    for line in lines:
        if y < 48:
            pdf.showPage()
            y = height - 48
            pdf.setFont("Helvetica", 10)
        pdf.drawString(48, y, line)
        y -= 18

    remarks = data.get("remarks")
    if remarks:
        if y < 72:
            pdf.showPage()
            y = height - 48
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(48, y, "Remarks")
        y -= 18
        pdf.setFont("Helvetica", 10)
        pdf.drawString(48, y, str(remarks)[:500])

    pdf.save()
    buffer.seek(0)
    return buffer.read()
