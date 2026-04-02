import { describe, expect, it } from 'vitest';

import { groupStudentTimetableByDay } from './timetablePage.helpers';

describe('groupStudentTimetableByDay', () => {
  it('groups rows by day, sorts rows by time, and enriches them from offerings', () => {
    const result = groupStudentTimetableByDay(
      [
        { id: '2', day: 'Tuesday', start_time: '10:00', end_time: '11:00', course_offering_id: 'off-2' },
        { id: '1', day: 'Monday', start_time: '11:00', end_time: '12:00', course_offering_id: 'off-1' },
        { id: '3', day: 'Monday', start_time: '09:00', end_time: '10:00', course_offering_id: 'off-1' }
      ],
      {
        'off-1': {
          subject_name: 'Distributed Systems',
          teacher_name: 'Prof. Rao',
          group_name: 'Group A',
          offering_type: 'theory'
        },
        'off-2': {
          subject_code: 'CSE402',
          teacher_user_id: 'teacher-2',
          offering_type: 'practical'
        }
      }
    );

    expect(result.map((item) => item.day)).toEqual(['Monday', 'Tuesday']);
    expect(result[0].rows.map((row) => row.id)).toEqual(['3', '1']);
    expect(result[0].rows[0]).toMatchObject({
      subject: 'Distributed Systems',
      teacher: 'Prof. Rao',
      group: 'Group A',
      type: 'theory'
    });
    expect(result[1].rows[0]).toMatchObject({
      subject: 'CSE402',
      teacher: 'teacher-2',
      group: '',
      type: 'practical'
    });
  });

  it('returns an empty array when no slots are available', () => {
    expect(groupStudentTimetableByDay([], {})).toEqual([]);
  });
});
