import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import SearchableSelect from '../components/ui/SearchableSelect';
import Table from '../components/ui/Table';
import {
  assignSectionRepresentative,
  createSection,
  getSectionRepresentatives,
  getSections,
  removeSectionRepresentative
} from '../services/sectionsApi';
import { apiClient } from '../services/apiClient';
import { searchLookupOptions } from '../services/paginatedLookups';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';

export default function ClassesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const isYearHead = user?.role === 'teacher' && (user?.extended_roles || []).includes('year_head');
  const canManageRepresentatives = isAdmin || isYearHead;
  const canHydrateUserProfiles = isAdmin;
  const { pushToast } = useToast();

  const [rows, setRows] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [teachers, setTeachers] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedRepresentativeSectionId, setSelectedRepresentativeSectionId] = useState('');
  const [representativesData, setRepresentativesData] = useState(null);
  const [representativesLoading, setRepresentativesLoading] = useState(false);
  const [representativeDrafts, setRepresentativeDrafts] = useState({
    cr_1: { student_user_id: '', reason: '' },
    cr_2: { student_user_id: '', reason: '' }
  });
  const [representativeActionSeat, setRepresentativeActionSeat] = useState('');
  const [representativeConfirmSeat, setRepresentativeConfirmSeat] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);

  const [filters, setFilters] = useState({
    faculty_id: '',
    department_id: '',
    program_id: '',
    specialization_id: '',
    batch_id: '',
    semester_id: ''
  });

  const [form, setForm] = useState({
    faculty_id: '',
    department_id: '',
    program_id: '',
    specialization_id: '',
    batch_id: '',
    semester_id: '',
    name: '',
    class_coordinator_user_id: ''
  });

  function entityLabel(item, fallbackLabel) {
    if (!item) return fallbackLabel || '';
    return item.display_label || (item.public_id ? `${item.name || fallbackLabel || ''} (${item.public_id})` : item.name || fallbackLabel || '');
  }

  const facultyNameById = useMemo(() => Object.fromEntries(faculties.map((item) => [item.id, entityLabel(item, 'Faculty')])), [faculties]);
  const departmentNameById = useMemo(() => Object.fromEntries(departments.map((item) => [item.id, entityLabel(item, 'Department')])), [departments]);
  const programNameById = useMemo(() => Object.fromEntries(programs.map((item) => [item.id, entityLabel(item, 'Program')])), [programs]);
  const specializationNameById = useMemo(
    () => Object.fromEntries(specializations.map((item) => [item.id, entityLabel(item, 'Specialization')])),
    [specializations]
  );
  const batchById = useMemo(() => Object.fromEntries(batches.map((item) => [item.id, item])), [batches]);
  const batchNameById = useMemo(() => Object.fromEntries(batches.map((item) => [item.id, entityLabel(item, 'Batch')])), [batches]);
  const semesterLabelById = useMemo(
    () => Object.fromEntries(semesters.map((item) => [item.id, item.display_label || item.label || item.public_id || 'Semester'])),
    [semesters]
  );
  const teacherNameById = useMemo(() => Object.fromEntries(teachers.map((item) => [item.id, item.full_name])), [teachers]);

  const selectedFormBatch = form.batch_id ? batchById[form.batch_id] || null : null;
  const selectedFilterBatch = filters.batch_id ? batchById[filters.batch_id] || null : null;
  const formBatchSpecializationId = selectedFormBatch?.specialization_id || '';
  const filterBatchSpecializationId = selectedFilterBatch?.specialization_id || '';

  const availableDepartmentsForForm = useMemo(
    () => departments.filter((item) => !form.faculty_id || item.faculty_id === form.faculty_id),
    [departments, form.faculty_id]
  );
  const availableProgramsForForm = useMemo(
    () => programs.filter((item) => !form.department_id || item.department_id === form.department_id),
    [programs, form.department_id]
  );
  const availableSpecializationsForForm = useMemo(
    () => {
      if (formBatchSpecializationId) {
        return specializations.filter((item) => item.id === formBatchSpecializationId);
      }
      if (selectedFormBatch && !selectedFormBatch.specialization_id) {
        return [];
      }
      return specializations.filter((item) => !form.program_id || item.program_id === form.program_id);
    },
    [form.program_id, formBatchSpecializationId, selectedFormBatch, specializations]
  );
  const availableBatchesForForm = useMemo(
    () =>
      batches.filter(
        (item) =>
          (!form.program_id || item.program_id === form.program_id) &&
          (!form.specialization_id || item.specialization_id === form.specialization_id)
      ),
    [batches, form.program_id, form.specialization_id]
  );
  const availableSemestersForForm = useMemo(
    () => semesters.filter((item) => !form.batch_id || item.batch_id === form.batch_id),
    [semesters, form.batch_id]
  );

  const availableDepartmentsForFilters = useMemo(
    () => departments.filter((item) => !filters.faculty_id || item.faculty_id === filters.faculty_id),
    [departments, filters.faculty_id]
  );
  const availableProgramsForFilters = useMemo(
    () => programs.filter((item) => !filters.department_id || item.department_id === filters.department_id),
    [programs, filters.department_id]
  );
  const availableSpecializationsForFilters = useMemo(
    () => {
      if (filterBatchSpecializationId) {
        return specializations.filter((item) => item.id === filterBatchSpecializationId);
      }
      if (selectedFilterBatch && !selectedFilterBatch.specialization_id) {
        return [];
      }
      return specializations.filter((item) => !filters.program_id || item.program_id === filters.program_id);
    },
    [filterBatchSpecializationId, filters.program_id, selectedFilterBatch, specializations]
  );
  const availableBatchesForFilters = useMemo(
    () =>
      batches.filter(
        (item) =>
          (!filters.program_id || item.program_id === filters.program_id) &&
          (!filters.specialization_id || item.specialization_id === filters.specialization_id)
      ),
    [batches, filters.program_id, filters.specialization_id]
  );
  const availableSemestersForFilters = useMemo(
    () => semesters.filter((item) => !filters.batch_id || item.batch_id === filters.batch_id),
    [semesters, filters.batch_id]
  );

  function mergeRows(setter, rows) {
    setter((prev) => {
      const merged = new Map((prev || []).map((item) => [String(item.id), item]));
      (rows || []).forEach((item) => {
        if (item?.id) {
          merged.set(String(item.id), item);
        }
      });
      return Array.from(merged.values());
    });
  }

  async function hydrateRows(loadedRows) {
    const facultyIds = Array.from(new Set((loadedRows || []).map((item) => item.faculty_id).filter(Boolean)));
    const departmentIds = Array.from(new Set((loadedRows || []).map((item) => item.department_id).filter(Boolean)));
    const programIds = Array.from(new Set((loadedRows || []).map((item) => item.program_id).filter(Boolean)));
    const specializationIds = Array.from(new Set((loadedRows || []).map((item) => item.specialization_id).filter(Boolean)));
    const batchIds = Array.from(new Set((loadedRows || []).map((item) => item.batch_id).filter(Boolean)));
    const semesterIds = Array.from(new Set((loadedRows || []).map((item) => item.semester_id).filter(Boolean)));
    const teacherIds = Array.from(new Set((loadedRows || []).map((item) => item.class_coordinator_user_id).filter(Boolean)));

    const knownFacultyIds = new Set(faculties.map((item) => item.id));
    const knownDepartmentIds = new Set(departments.map((item) => item.id));
    const knownProgramIds = new Set(programs.map((item) => item.id));
    const knownSpecializationIds = new Set(specializations.map((item) => item.id));
    const knownBatchIds = new Set(batches.map((item) => item.id));
    const knownSemesterIds = new Set(semesters.map((item) => item.id));
    const knownTeacherIds = new Set(teachers.map((item) => item.id));

    const teacherProfileRequests = canHydrateUserProfiles
      ? Promise.allSettled(teacherIds.filter((id) => !knownTeacherIds.has(id)).map((id) => apiClient.get(`/users/${id}`)))
      : Promise.resolve([]);
    const [facultyResponses, departmentResponses, programResponses, specializationResponses, batchResponses, semesterResponses, teacherResponses] =
      await Promise.all([
        Promise.allSettled(facultyIds.filter((id) => !knownFacultyIds.has(id)).map((id) => apiClient.get(`/faculties/${id}`))),
        Promise.allSettled(departmentIds.filter((id) => !knownDepartmentIds.has(id)).map((id) => apiClient.get(`/departments/${id}`))),
        Promise.allSettled(programIds.filter((id) => !knownProgramIds.has(id)).map((id) => apiClient.get(`/programs/${id}`))),
        Promise.allSettled(specializationIds.filter((id) => !knownSpecializationIds.has(id)).map((id) => apiClient.get(`/specializations/${id}`))),
        Promise.allSettled(batchIds.filter((id) => !knownBatchIds.has(id)).map((id) => apiClient.get(`/batches/${id}`))),
        Promise.allSettled(semesterIds.filter((id) => !knownSemesterIds.has(id)).map((id) => apiClient.get(`/semesters/${id}`))),
        teacherProfileRequests
      ]);

    mergeRows(setFaculties, facultyResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data));
    mergeRows(setDepartments, departmentResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data));
    mergeRows(setPrograms, programResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data));
    mergeRows(
      setSpecializations,
      specializationResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data)
    );
    mergeRows(setBatches, batchResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data));
    mergeRows(setSemesters, semesterResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data));
    mergeRows(
      setTeachers,
      teacherResponses.filter((result) => result.status === 'fulfilled').map((result) => result.value.data)
    );
  }

  async function loadFacultyOptions(query) {
    const options = await searchLookupOptions({
      path: '/faculties/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({ value: item.id, label: item.display_label || item.name, ...item })
    });
    mergeRows(setFaculties, options.map((item) => ({ id: item.value, name: item.name || item.label, public_id: item.public_id, display_label: item.display_label })));
    return options;
  }

  async function loadDepartmentOptions(query, facultyId) {
    if (!facultyId) return [];
    const options = await searchLookupOptions({
      path: '/departments/',
      q: query,
      params: { is_active: true, faculty_id: facultyId },
      mapOption: (item) => ({ value: item.id, label: item.display_label || item.name, faculty_id: item.faculty_id, ...item })
    });
    mergeRows(setDepartments, options.map((item) => ({ id: item.value, name: item.name || item.label, faculty_id: item.faculty_id, public_id: item.public_id, display_label: item.display_label })));
    return options;
  }

  async function loadProgramOptions(query, departmentId) {
    if (!departmentId) return [];
    const options = await searchLookupOptions({
      path: '/programs/',
      q: query,
      params: { is_active: true, department_id: departmentId },
      mapOption: (item) => ({ value: item.id, label: item.display_label || item.name, department_id: item.department_id, ...item })
    });
    mergeRows(setPrograms, options.map((item) => ({ id: item.value, name: item.name || item.label, department_id: item.department_id, public_id: item.public_id, display_label: item.display_label })));
    return options;
  }

  async function loadSpecializationOptions(query, programId) {
    if (!programId) return [];
    const options = await searchLookupOptions({
      path: '/specializations/',
      q: query,
      params: { is_active: true, program_id: programId },
      mapOption: (item) => ({ value: item.id, label: item.display_label || item.name, program_id: item.program_id, ...item })
    });
    mergeRows(setSpecializations, options.map((item) => ({ id: item.value, name: item.name || item.label, program_id: item.program_id, public_id: item.public_id, display_label: item.display_label })));
    return options;
  }

  async function loadBatchOptions(query, programId, specializationId) {
    if (!programId) return [];
    const options = await searchLookupOptions({
      path: '/batches/',
      q: query,
      params: { is_active: true, program_id: programId, specialization_id: specializationId || undefined },
      mapOption: (item) => ({
        value: item.id,
        label: item.display_label || item.name,
        program_id: item.program_id,
        specialization_id: item.specialization_id,
        ...item
      })
    });
    mergeRows(
      setBatches,
      options.map((item) => ({
        id: item.value,
        name: item.name || item.label,
        public_id: item.public_id,
        display_label: item.display_label,
        program_id: item.program_id,
        specialization_id: item.specialization_id
      }))
    );
    return options;
  }

  async function loadSemesterOptions(query, batchId) {
    if (!batchId) return [];
    const options = await searchLookupOptions({
      path: '/semesters/',
      q: query,
      params: { is_active: true, batch_id: batchId },
      mapOption: (item) => ({ value: item.id, label: item.display_label || item.label, batch_id: item.batch_id, ...item })
    });
    mergeRows(setSemesters, options.map((item) => ({ id: item.value, label: item.label, batch_id: item.batch_id, public_id: item.public_id, display_label: item.display_label })));
    return options;
  }

  async function loadTeacherOptions(query) {
    if (!isAdmin) return [];
    const options = await searchLookupOptions({
      path: '/users/',
      q: query,
      params: { role: 'teacher', is_active: true, limit: 20 },
      mapOption: (item) => ({ value: item.id, label: `${item.full_name} (${item.email})`, full_name: item.full_name, ...item })
    });
    mergeRows(
      setTeachers,
      options.map((item) => ({ id: item.value, full_name: item.full_name || item.label }))
    );
    return options;
  }

  async function loadSections() {
    setLoading(true);
    setError('');
    try {
      const response = await getSections({
        faculty_id: filters.faculty_id || undefined,
        department_id: filters.department_id || undefined,
        program_id: filters.program_id || undefined,
        specialization_id: filters.specialization_id || undefined,
        batch_id: filters.batch_id || undefined,
        semester_id: filters.semester_id || undefined,
        skip,
        limit
      });
      setRows(response.data || []);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load sections');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  function hydrateRepresentativeDrafts(data) {
    const reps = data?.representatives || {};
    setRepresentativeConfirmSeat('');
    setRepresentativeDrafts({
      cr_1: {
        student_user_id: reps?.cr_1?.user_id || '',
        reason: ''
      },
      cr_2: {
        student_user_id: reps?.cr_2?.user_id || '',
        reason: ''
      }
    });
  }

  async function loadRepresentatives(sectionId) {
    if (!sectionId || !canManageRepresentatives) return;
    setSelectedRepresentativeSectionId(sectionId);
    setRepresentativesLoading(true);
    try {
      const data = await getSectionRepresentatives(sectionId);
      setRepresentativesData(data || null);
      hydrateRepresentativeDrafts(data);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load class representatives');
      pushToast({ title: 'Representative load failed', description: message, variant: 'error' });
    } finally {
      setRepresentativesLoading(false);
    }
  }

  async function handleAssignRepresentative(seat) {
    const sectionId = selectedRepresentativeSectionId;
    const draft = representativeDrafts[seat] || {};
    const seatState = representativesData?.representatives?.[seat] || {};
    if (!sectionId || !draft.student_user_id || !draft.reason.trim()) {
      pushToast({ title: 'Missing details', description: 'Select a student and provide a reason before assigning the seat.', variant: 'error' });
      return;
    }
    if (seatState.user_id && seatState.user_id !== draft.student_user_id && representativeConfirmSeat !== seat) {
      setRepresentativeConfirmSeat(seat);
      pushToast({ title: 'Confirm replacement', description: 'Click Confirm Replace to replace the existing CR seat occupant.', variant: 'info' });
      return;
    }
    setRepresentativeActionSeat(seat);
    try {
      const data = await assignSectionRepresentative(sectionId, seat, {
        student_user_id: draft.student_user_id,
        reason: draft.reason.trim()
      });
      setRepresentativeConfirmSeat('');
      setRepresentativesData(data || null);
      hydrateRepresentativeDrafts(data);
      await loadSections();
      pushToast({ title: 'Representative updated', description: `${seat.toUpperCase()} assignment saved.`, variant: 'success' });
    } catch (err) {
      const message = formatApiError(err, 'Failed to assign class representative');
      pushToast({ title: 'Assignment failed', description: message, variant: 'error' });
    } finally {
      setRepresentativeActionSeat('');
    }
  }

  async function handleRemoveRepresentative(seat) {
    const sectionId = selectedRepresentativeSectionId;
    const draft = representativeDrafts[seat] || {};
    if (!sectionId || !draft.reason.trim()) {
      pushToast({ title: 'Reason required', description: 'Provide a reason before removing the representative seat.', variant: 'error' });
      return;
    }
    setRepresentativeActionSeat(seat);
    try {
      const data = await removeSectionRepresentative(sectionId, seat, { reason: draft.reason.trim() });
      setRepresentativesData(data || null);
      hydrateRepresentativeDrafts(data);
      await loadSections();
      pushToast({ title: 'Representative removed', description: `${seat.toUpperCase()} has been cleared.`, variant: 'success' });
    } catch (err) {
      const message = formatApiError(err, 'Failed to remove class representative');
      pushToast({ title: 'Remove failed', description: message, variant: 'error' });
    } finally {
      setRepresentativeActionSeat('');
    }
  }

  useEffect(() => {
    loadSections();
  }, [skip, limit, filters]);

  useEffect(() => {
    hydrateRows(rows);
  }, [rows]);

  function handleFormBatchChange(batchId) {
    const nextBatch = batchId ? batchById[batchId] || null : null;
    setForm((prev) => ({
      ...prev,
      batch_id: batchId,
      semester_id: '',
      specialization_id: nextBatch?.specialization_id || ''
    }));
  }

  function handleFilterBatchChange(batchId) {
    const nextBatch = batchId ? batchById[batchId] || null : null;
    setFilters((prev) => ({
      ...prev,
      batch_id: batchId,
      semester_id: '',
      specialization_id: nextBatch?.specialization_id || ''
    }));
  }

  async function onCreate(event) {
    event.preventDefault();
    try {
      await createSection({
        faculty_id: form.faculty_id || null,
        department_id: form.department_id || null,
        program_id: form.program_id || null,
        specialization_id: form.specialization_id || null,
        batch_id: form.batch_id || null,
        semester_id: form.semester_id || null,
        name: form.name,
        class_coordinator_user_id: form.class_coordinator_user_id || null,
        faculty_name: facultyNameById[form.faculty_id] || null
      });
      pushToast({ title: 'Created', description: 'Section created successfully.', variant: 'success' });
      setForm({
        faculty_id: '',
        department_id: '',
        program_id: '',
        specialization_id: '',
        batch_id: '',
        semester_id: '',
        name: '',
        class_coordinator_user_id: ''
      });
      setSkip(0);
      await loadSections();
    } catch (err) {
      const message = formatApiError(err, 'Failed to create section');
      setError(message);
      pushToast({ title: 'Create failed', description: message, variant: 'error' });
    }
  }

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Section' },
      { key: 'public_id', label: 'Short ID', render: (row) => row.public_id || '-' },
      { key: 'faculty_id', label: 'Faculty', render: (row) => facultyNameById[row.faculty_id] || '-' },
      { key: 'department_id', label: 'Department', render: (row) => departmentNameById[row.department_id] || '-' },
      { key: 'program_id', label: 'Program', render: (row) => programNameById[row.program_id] || '-' },
      {
        key: 'specialization_id',
        label: 'Specialization',
        render: (row) => specializationNameById[row.specialization_id] || '-'
      },
      { key: 'batch_id', label: 'Batch', render: (row) => batchNameById[row.batch_id] || '-' },
      { key: 'semester_id', label: 'Semester', render: (row) => semesterLabelById[row.semester_id] || '-' },
      {
        key: 'class_coordinator_user_id',
        label: 'Coordinator',
        render: (row) =>
          row.class_coordinator_user_id
            ? teacherNameById[row.class_coordinator_user_id] || '-'
            : '-'
      },
      {
        key: 'cr_1',
        label: 'CR-1',
        render: (row) => row.class_representatives?.cr_1?.full_name || '-'
      },
      {
        key: 'cr_2',
        label: 'CR-2',
        render: (row) => row.class_representatives?.cr_2?.full_name || '-'
      },
      ...(canManageRepresentatives
        ? [
            {
              key: 'manage_representatives',
              label: 'Representatives',
              render: (row) => (
                <button type="button" className="btn-secondary !px-3 !py-1.5 text-xs" onClick={() => void loadRepresentatives(row.id)}>
                  {selectedRepresentativeSectionId === row.id ? 'Refresh CRs' : 'Manage CRs'}
                </button>
              )
            }
          ]
        : [])
    ],
    [
      batchNameById,
      canManageRepresentatives,
      departmentNameById,
      facultyNameById,
      loadRepresentatives,
      programNameById,
      selectedRepresentativeSectionId,
      semesterLabelById,
      specializationNameById,
      teacherNameById
    ]
  );

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Sections</h1>
          <button className="btn-secondary" onClick={() => { setSkip(0); loadSections(); }}>Refresh</button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <SearchableSelect
            label="Faculty"
            value={filters.faculty_id}
            options={faculties.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={loadFacultyOptions}
            selectedLabel={facultyNameById[filters.faculty_id] || ''}
            allowEmpty
            emptyLabel="All Faculties"
            placeholder="Search faculty"
            onValueChange={(value) => setFilters((prev) => ({ ...prev, faculty_id: value, department_id: '', program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}
          />
          <SearchableSelect
            label="Department"
            value={filters.department_id}
            options={availableDepartmentsForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadDepartmentOptions(query, filters.faculty_id)}
            selectedLabel={departmentNameById[filters.department_id] || ''}
            allowEmpty
            disabled={!filters.faculty_id}
            emptyLabel="All Departments"
            placeholder={filters.faculty_id ? 'Search department' : 'Select faculty first'}
            onValueChange={(value) => setFilters((prev) => ({ ...prev, department_id: value, program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}
          />
          <SearchableSelect
            label="Program"
            value={filters.program_id}
            options={availableProgramsForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadProgramOptions(query, filters.department_id)}
            selectedLabel={programNameById[filters.program_id] || ''}
            allowEmpty
            disabled={!filters.department_id}
            emptyLabel="All Programs"
            placeholder={filters.department_id ? 'Search program' : 'Select department first'}
            onValueChange={(value) => setFilters((prev) => ({ ...prev, program_id: value, specialization_id: '', batch_id: '', semester_id: '' }))}
          />
          <SearchableSelect
            label="Specialization"
            value={filters.specialization_id}
            options={availableSpecializationsForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadSpecializationOptions(query, filters.program_id)}
            selectedLabel={specializationNameById[filters.specialization_id] || ''}
            allowEmpty
            disabled={Boolean(selectedFilterBatch) || !filters.program_id}
            emptyLabel={
              selectedFilterBatch
                ? selectedFilterBatch.specialization_id
                  ? 'Batch specialization'
                  : 'Program-level batch'
                : 'All Specializations'
            }
            placeholder={filters.program_id ? 'Search specialization' : 'Select program first'}
            onValueChange={(value) => setFilters((prev) => ({ ...prev, specialization_id: value, batch_id: '', semester_id: '' }))}
          />
          <SearchableSelect
            label="Batch"
            value={filters.batch_id}
            options={availableBatchesForFilters.map((item) => ({ value: item.id, label: item.name }))}
            loadOptions={(query) => loadBatchOptions(query, filters.program_id, filters.specialization_id)}
            selectedLabel={batchNameById[filters.batch_id] || ''}
            allowEmpty
            disabled={!filters.program_id}
            emptyLabel="All Batches"
            placeholder={filters.program_id ? 'Search batch' : 'Select program first'}
            onValueChange={handleFilterBatchChange}
          />
          <SearchableSelect
            label="Semester"
            value={filters.semester_id}
            options={availableSemestersForFilters.map((item) => ({ value: item.id, label: item.label }))}
            loadOptions={(query) => loadSemesterOptions(query, filters.batch_id)}
            selectedLabel={semesterLabelById[filters.semester_id] || ''}
            allowEmpty
            disabled={!filters.batch_id}
            emptyLabel="All Semesters"
            placeholder={filters.batch_id ? 'Search semester' : 'Select batch first'}
            onValueChange={(value) => setFilters((prev) => ({ ...prev, semester_id: value }))}
          />
        </div>
      </Card>

      {isAdmin ? (
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Create Section</h2>
          <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <SearchableSelect
              label="Faculty"
              value={form.faculty_id}
              options={faculties.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={loadFacultyOptions}
              selectedLabel={facultyNameById[form.faculty_id] || ''}
              placeholder="Search faculty"
              onValueChange={(value) => setForm((prev) => ({ ...prev, faculty_id: value, department_id: '', program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}
              required
            />
            <SearchableSelect
              label="Department"
              value={form.department_id}
              options={availableDepartmentsForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadDepartmentOptions(query, form.faculty_id)}
              selectedLabel={departmentNameById[form.department_id] || ''}
              disabled={!form.faculty_id}
              placeholder={form.faculty_id ? 'Search department' : 'Select faculty first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, department_id: value, program_id: '', specialization_id: '', batch_id: '', semester_id: '' }))}
              required
            />
            <SearchableSelect
              label="Program"
              value={form.program_id}
              options={availableProgramsForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadProgramOptions(query, form.department_id)}
              selectedLabel={programNameById[form.program_id] || ''}
              disabled={!form.department_id}
              placeholder={form.department_id ? 'Search program' : 'Select department first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, program_id: value, specialization_id: '', batch_id: '', semester_id: '' }))}
              required
            />
            <SearchableSelect
              label="Specialization"
              value={form.specialization_id}
              options={availableSpecializationsForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadSpecializationOptions(query, form.program_id)}
              selectedLabel={specializationNameById[form.specialization_id] || ''}
              disabled={Boolean(selectedFormBatch) || !form.program_id}
              allowEmpty
              emptyLabel={
                selectedFormBatch
                  ? selectedFormBatch.specialization_id
                    ? 'Locked to batch specialization'
                    : 'Program-level batch'
                  : 'Select Specialization'
              }
              placeholder={form.program_id ? 'Search specialization' : 'Select program first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, specialization_id: value, batch_id: '', semester_id: '' }))}
            />
            <SearchableSelect
              label="Batch"
              value={form.batch_id}
              options={availableBatchesForForm.map((item) => ({ value: item.id, label: item.name }))}
              loadOptions={(query) => loadBatchOptions(query, form.program_id, form.specialization_id)}
              selectedLabel={batchNameById[form.batch_id] || ''}
              disabled={!form.program_id}
              placeholder={form.program_id ? 'Search batch' : 'Select program first'}
              onValueChange={handleFormBatchChange}
              required
            />
            <SearchableSelect
              label="Semester"
              value={form.semester_id}
              options={availableSemestersForForm.map((item) => ({ value: item.id, label: item.label }))}
              loadOptions={(query) => loadSemesterOptions(query, form.batch_id)}
              selectedLabel={semesterLabelById[form.semester_id] || ''}
              disabled={!form.batch_id}
              placeholder={form.batch_id ? 'Search semester' : 'Select batch first'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, semester_id: value }))}
              required
            />
            <label className="block space-y-1">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Section Name</span>
              <input className="input" required value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} placeholder="e.g. CSE 4A" />
            </label>
            <SearchableSelect
              label="Coordinator"
              value={form.class_coordinator_user_id}
              options={teachers.map((teacher) => ({ value: teacher.id, label: teacher.full_name }))}
              loadOptions={loadTeacherOptions}
              selectedLabel={teacherNameById[form.class_coordinator_user_id] || ''}
              disabled={!isAdmin}
              allowEmpty
              emptyLabel="No Coordinator"
              placeholder={isAdmin ? 'Search teacher' : 'Unavailable'}
              onValueChange={(value) => setForm((prev) => ({ ...prev, class_coordinator_user_id: value }))}
            />
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full">Create</button>
            </div>
          </form>
        </Card>
      ) : null}

      {canManageRepresentatives && selectedRepresentativeSectionId ? (
        <Card className="space-y-4 border-brand-100 bg-gradient-to-br from-white via-brand-50/40 to-slate-50 dark:border-brand-950/40 dark:from-slate-950 dark:via-slate-900 dark:to-brand-950/20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">Section Governance</p>
              <h2 className="mt-1 text-lg font-semibold">Class Representative Seats</h2>
              <p className="mt-1 text-sm text-slate-500">
                Manage CR-1 and CR-2 for {representativesData?.section_name || selectedRepresentativeSectionId}.
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200">
                  Read-only student access
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  Max 2 seats per section
                </span>
                <span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
                  Reason required for audit
                </span>
              </div>
            </div>
            <button type="button" className="btn-secondary" onClick={() => void loadRepresentatives(selectedRepresentativeSectionId)} disabled={representativesLoading}>
              {representativesLoading ? 'Refreshing...' : 'Refresh Seats'}
            </button>
          </div>

          {representativesLoading ? <p className="text-sm text-slate-500">Loading representative seats...</p> : null}

          <div className="grid gap-4 lg:grid-cols-2">
            {['cr_1', 'cr_2'].map((seat) => {
              const seatState = representativesData?.representatives?.[seat] || {};
              const draft = representativeDrafts[seat] || { student_user_id: '', reason: '' };
              const seatCandidates = representativesData?.candidate_students || [];
              const seatLabel = seat.replace('_', '-').toUpperCase();
              const replacingSeat = Boolean(seatState.user_id && draft.student_user_id && seatState.user_id !== draft.student_user_id);
              const readyToAssign = Boolean(draft.student_user_id && draft.reason?.trim());
              const readyToClear = Boolean(seatState.user_id && draft.reason?.trim());
              const selectedCandidate = seatCandidates.find((candidate) => candidate.student_user_id === draft.student_user_id);
              return (
                <div key={seat} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-950/50">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-600">{seatLabel}</p>
                      <p className="mt-2 text-base font-semibold text-slate-900 dark:text-slate-100">{seatState.full_name || 'Unassigned'}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {seatState.user_id ? 'Changing this seat requires a reason and replacement confirmation.' : 'Assign one active student from this section.'}
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${seatState.user_id ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
                      {seatState.user_id ? 'Assigned' : 'Empty'}
                    </span>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300">
                      <span className="font-semibold text-slate-800 dark:text-slate-100">Current holder:</span>{' '}
                      {seatState.full_name || 'No student assigned yet'}
                    </div>

                    <label className="block space-y-1">
                      <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Student</span>
                      <select
                        className="input"
                        value={draft.student_user_id || ''}
                        onChange={(event) => {
                          setRepresentativeDrafts((prev) => ({
                            ...prev,
                            [seat]: { ...(prev[seat] || {}), student_user_id: event.target.value }
                          }));
                          setRepresentativeConfirmSeat('');
                        }}
                      >
                        <option value="">Select Student</option>
                        {seatCandidates.map((candidate) => (
                          <option key={candidate.student_user_id} value={candidate.student_user_id}>
                            {candidate.full_name}
                          </option>
                        ))}
                      </select>
                      {!seatCandidates.length ? (
                        <p className="mt-1 text-xs text-amber-600 dark:text-amber-300">No active student candidates were found for this section.</p>
                      ) : null}
                    </label>

                    {selectedCandidate ? (
                      <div className="rounded-2xl border border-brand-100 bg-brand-50/70 px-3 py-2 text-xs text-brand-800 dark:border-brand-900/40 dark:bg-brand-950/20 dark:text-brand-200">
                        <span className="font-semibold">Selected candidate:</span> {selectedCandidate.full_name}
                        {replacingSeat ? ' will replace the current holder after confirmation.' : ' will receive read-only CR access for this section.'}
                      </div>
                    ) : null}

                    <label className="block space-y-1">
                      <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Reason</span>
                      <input
                        className="input"
                        value={draft.reason || ''}
                        onChange={(event) =>
                          setRepresentativeDrafts((prev) => ({
                            ...prev,
                            [seat]: { ...(prev[seat] || {}), reason: event.target.value }
                          }))
                        }
                        placeholder={`Reason for ${seat.replace('_', '-').toUpperCase()} change`}
                      />
                      <p className="text-xs text-slate-500">Reason is saved to the audit log for assignment, replacement, and removal.</p>
                    </label>

                    {replacingSeat ? (
                      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 shadow-sm dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                        This will replace {seatState.full_name || 'the current CR'} for {seatLabel}. Review the reason, then confirm replace.
                      </div>
                    ) : null}

                    <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-3 dark:border-slate-700">
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={representativeActionSeat === seat || !readyToAssign}
                        onClick={() => void handleAssignRepresentative(seat)}
                      >
                        {representativeActionSeat === seat
                          ? 'Saving...'
                          : replacingSeat && representativeConfirmSeat === seat
                            ? 'Confirm Replace'
                            : replacingSeat
                              ? 'Review Replace'
                              : 'Assign Seat'}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={representativeActionSeat === seat || !readyToClear}
                        onClick={() => void handleRemoveRepresentative(seat)}
                      >
                        Clear Seat
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Sections List</h2>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>Prev</button>
            <span className="text-xs text-slate-500">skip: {skip}</span>
            <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>Next</button>
            <select className="input w-24" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>
        </div>
        {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <Table columns={columns} data={rows} />
      </Card>
    </div>
  );
}
