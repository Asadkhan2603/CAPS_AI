import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function YearsPage() {
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    async function loadCourses() {
      try {
        const response = await apiClient.get('/courses/', { params: { skip: 0, limit: 100 } });
        setCourses(response.data || []);
      } catch {
        setCourses([]);
      }
    }
    loadCourses();
  }, []);

  const courseOptions = useMemo(
    () => courses.map((course) => ({ value: course.id, label: `${course.name} (${course.code})` })),
    [courses]
  );

  const courseNameById = useMemo(
    () => Object.fromEntries(courses.map((course) => [course.id, `${course.name} (${course.code})`])),
    [courses]
  );

  const filters = useMemo(
    () => [
      {
        name: 'course_id',
        label: 'Course',
        type: 'select',
        options: courseOptions,
        placeholder: 'All Courses'
      }
    ],
    [courseOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'course_id', label: 'Course', type: 'select', options: courseOptions, required: true },
      { name: 'year_number', label: 'Year Number', type: 'number', min: 1, max: 10, required: true, defaultValue: 1 },
      { name: 'label', label: 'Label', required: true }
    ],
    [courseOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'course_id', label: 'Course', render: (row) => courseNameById[row.course_id] || row.course_id },
      { key: 'year_number', label: 'Year' },
      { key: 'label', label: 'Label' }
    ],
    [courseNameById]
  );

  return (
    <EntityManager
      title="Years"
      endpoint="/years/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
      deleteReviewEnabled
    />
  );
}
