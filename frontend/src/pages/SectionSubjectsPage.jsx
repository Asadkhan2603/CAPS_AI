import { useEffect, useMemo, useState } from 'react';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';

export default function SectionSubjectsPage() {
  const [sections, setSections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);

  useEffect(() => {
    async function loadLookups() {
      try {
        const [sectionsRes, subjectsRes, usersRes] = await Promise.all([
          apiClient.get('/sections/', { params: { skip: 0, limit: 100 } }),
          apiClient.get('/subjects/', { params: { skip: 0, limit: 100 } }),
          apiClient.get('/users/')
        ]);
        setSections(sectionsRes.data || []);
        setSubjects(subjectsRes.data || []);
        setTeachers((usersRes.data || []).filter((user) => user.role === 'teacher'));
      } catch {
        setSections([]);
        setSubjects([]);
        setTeachers([]);
      }
    }
    loadLookups();
  }, []);

  const sectionOptions = useMemo(
    () =>
      sections.map((section) => ({
        value: section.id,
        label: `${section.name} (${section.program} - ${section.academic_year})`
      })),
    [sections]
  );
  const subjectOptions = useMemo(
    () =>
      subjects.map((subject) => ({
        value: subject.id,
        label: `${subject.name} (${subject.code})`
      })),
    [subjects]
  );
  const teacherOptions = useMemo(
    () =>
      teachers.map((teacher) => ({
        value: teacher.id,
        label: `${teacher.full_name} (${teacher.email})`
      })),
    [teachers]
  );

  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );
  const subjectNameById = useMemo(
    () => Object.fromEntries(subjectOptions.map((item) => [item.value, item.label])),
    [subjectOptions]
  );
  const teacherNameById = useMemo(
    () => Object.fromEntries(teacherOptions.map((item) => [item.value, item.label])),
    [teacherOptions]
  );

  const filters = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'subject_id', label: 'Subject', type: 'select', options: subjectOptions, placeholder: 'All Subjects' }
    ],
    [sectionOptions, subjectOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'section_id', label: 'Section', type: 'select', options: sectionOptions, required: true },
      { name: 'subject_id', label: 'Subject', type: 'select', options: subjectOptions, required: true },
      { name: 'teacher_user_id', label: 'Teacher', type: 'select', options: teacherOptions, nullable: true, placeholder: 'No Teacher' }
    ],
    [sectionOptions, subjectOptions, teacherOptions]
  );

  const columns = useMemo(
    () => [
      { key: 'section_id', label: 'Section', render: (row) => sectionNameById[row.section_id] || row.section_id },
      { key: 'subject_id', label: 'Subject', render: (row) => subjectNameById[row.subject_id] || row.subject_id },
      { key: 'teacher_user_id', label: 'Teacher', render: (row) => teacherNameById[row.teacher_user_id] || row.teacher_user_id || '-' },
      { key: 'is_active', label: 'Active', render: (row) => String(row.is_active) }
    ],
    [sectionNameById, subjectNameById, teacherNameById]
  );

  return (
    <EntityManager
      title="Section Subjects"
      endpoint="/section-subjects/"
      filters={filters}
      createFields={createFields}
      columns={columns}
      enableDelete
      createTransform={(payload) => ({
        ...payload,
        teacher_user_id: payload.teacher_user_id || null
      })}
    />
  );
}
