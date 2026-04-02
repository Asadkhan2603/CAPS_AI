const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export function groupStudentTimetableByDay(studentClassSlots, studentOfferingMap) {
  if (!studentClassSlots?.length) return [];

  const grouped = {};
  for (const slot of studentClassSlots) {
    const offering = studentOfferingMap?.[slot.course_offering_id] || {};
    const day = slot.day || 'Unknown';
    if (!grouped[day]) grouped[day] = [];
    grouped[day].push({
      ...slot,
      subject: offering.subject_name || offering.subject_code || offering.subject_id || 'Subject',
      teacher: offering.teacher_name || offering.teacher_user_id || 'Teacher',
      group: offering.group_name || '',
      type: offering.offering_type || '-'
    });
  }

  return Object.entries(grouped)
    .map(([day, rows]) => ({
      day,
      rows: [...rows].sort((a, b) => String(a.start_time).localeCompare(String(b.start_time)))
    }))
    .sort((a, b) => DAY_ORDER.indexOf(a.day) - DAY_ORDER.indexOf(b.day));
}
