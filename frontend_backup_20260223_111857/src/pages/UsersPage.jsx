import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, X } from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { getAllSections } from '../services/sectionsApi';
import { useToast } from '../hooks/useToast';
import { cn } from '../utils/cn';

const PERMISSION_OPTIONS = {
  teacher: ['year_head', 'class_coordinator', 'club_coordinator'],
  student: ['club_president']
};

function FlipButton({ checked, disabled, onClick, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-2 py-1 text-xs transition',
        checked
          ? 'border-brand-400 bg-brand-100 text-brand-700 dark:border-brand-600 dark:bg-brand-900/30 dark:text-brand-300'
          : 'border-slate-300 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300',
        disabled && 'cursor-not-allowed opacity-60'
      )}
    >
      <span
        className={cn(
          'relative h-5 w-9 rounded-full transition-colors',
          checked ? 'bg-brand-500' : 'bg-slate-300 dark:bg-slate-700'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform',
            checked ? 'left-4' : 'left-0.5'
          )}
        />
      </span>
      <span>{label}</span>
    </button>
  );
}

export default function UsersPage() {
  const { pushToast } = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [teacherSearch, setTeacherSearch] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [openTeachers, setOpenTeachers] = useState(true);
  const [openStudents, setOpenStudents] = useState(true);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedTab, setSelectedTab] = useState('details');
  const [draftRoles, setDraftRoles] = useState({});
  const [draftScopes, setDraftScopes] = useState({});
  const [savingIds, setSavingIds] = useState([]);

  const [departments, setDepartments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [years, setYears] = useState([]);
  const [sections, setSections] = useState([]);
  const [clubs, setClubs] = useState([]);

  async function loadUsers() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/users/');
      setRows(response.data || []);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to load users';
      setError(String(detail));
      pushToast({ title: 'Load failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  async function loadLookups() {
    const [departmentsRes, coursesRes, yearsRes, sectionsRes, clubsRes] = await Promise.allSettled([
      apiClient.get('/departments/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/courses/', { params: { skip: 0, limit: 100 } }),
      apiClient.get('/years/', { params: { skip: 0, limit: 100 } }),
      getAllSections(100),
      apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } })
    ]);
    setDepartments(departmentsRes.status === 'fulfilled' ? (departmentsRes.value.data || []) : []);
    setCourses(coursesRes.status === 'fulfilled' ? (coursesRes.value.data || []) : []);
    setYears(yearsRes.status === 'fulfilled' ? (yearsRes.value.data || []) : []);
    setSections(sectionsRes.status === 'fulfilled' ? (sectionsRes.value || []) : []);
    setClubs(clubsRes.status === 'fulfilled' ? (clubsRes.value.data || []) : []);
  }

  useEffect(() => {
    loadUsers();
    loadLookups();
  }, []);

  const selectedUser = useMemo(
    () => rows.find((item) => item.id === selectedUserId) || null,
    [rows, selectedUserId]
  );

  useEffect(() => {
    if (selectedUser) {
      setSelectedTab('details');
    }
  }, [selectedUserId]);

  function getEffectiveExtensions(row) {
    return draftRoles[row.id] ?? row.extended_roles ?? [];
  }

  function getEffectiveScope(row) {
    return draftScopes[row.id] ?? row.role_scope ?? {};
  }

  function setScopeForUser(row, nextScope) {
    setDraftScopes((prev) => ({ ...prev, [row.id]: nextScope }));
  }

  function updateClassCoordinatorScope(row, patch) {
    const current = getEffectiveScope(row);
    const existing = current.class_coordinator || {};
    setScopeForUser(row, {
      ...current,
      class_coordinator: { ...existing, ...patch }
    });
  }

  function updateClubPresidentScope(row, patch) {
    const current = getEffectiveScope(row);
    const existing = current.club_president || {};
    setScopeForUser(row, {
      ...current,
      club_president: { ...existing, ...patch }
    });
  }

  function toggleExtension(row, extension) {
    const current = getEffectiveExtensions(row);
    const next = current.includes(extension) ? current.filter((item) => item !== extension) : [...current, extension];
    setDraftRoles((prev) => ({ ...prev, [row.id]: next }));
  }

  async function savePermissions(row) {
    const nextRoles = getEffectiveExtensions(row);
    const nextScope = getEffectiveScope(row);
    setSavingIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    try {
      await apiClient.patch(`/users/${row.id}/extensions`, { extended_roles: nextRoles, role_scope: nextScope });
      setRows((prev) =>
        prev.map((item) =>
          item.id === row.id ? { ...item, extended_roles: nextRoles, role_scope: nextScope } : item
        )
      );
      setDraftRoles((prev) => {
        const copy = { ...prev };
        delete copy[row.id];
        return copy;
      });
      setDraftScopes((prev) => {
        const copy = { ...prev };
        delete copy[row.id];
        return copy;
      });
      pushToast({ title: 'Updated', description: 'Permissions updated successfully.', variant: 'success' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update permissions';
      pushToast({ title: 'Update failed', description: String(detail), variant: 'error' });
    } finally {
      setSavingIds((prev) => prev.filter((id) => id !== row.id));
    }
  }

  const teacherRows = useMemo(() => {
    const needle = teacherSearch.trim().toLowerCase();
    const base = rows.filter((row) => row.role === 'teacher');
    if (!needle) return base;
    return base.filter(
      (row) =>
        row.full_name?.toLowerCase().includes(needle) || row.email?.toLowerCase().includes(needle)
    );
  }, [rows, teacherSearch]);

  const studentRows = useMemo(() => {
    const needle = studentSearch.trim().toLowerCase();
    const base = rows.filter((row) => row.role === 'student');
    if (!needle) return base;
    return base.filter(
      (row) =>
        row.full_name?.toLowerCase().includes(needle) || row.email?.toLowerCase().includes(needle)
    );
  }, [rows, studentSearch]);

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'email', label: 'Email' },
      { key: 'role', label: 'Role' },
      {
        key: 'extended_roles',
        label: 'Permissions',
        render: (row) => {
          const current = getEffectiveExtensions(row);
          return current.length ? current.join(', ') : '-';
        }
      }
    ],
    [draftRoles]
  );

  const clickableColumns = useMemo(
    () =>
      columns.map((column) =>
        column.key === 'full_name'
          ? {
              ...column,
              render: (row) => (
                <button
                  type="button"
                  className="text-left font-medium text-brand-600 underline-offset-2 hover:underline dark:text-brand-300"
                  onClick={() => setSelectedUserId(row.id)}
                >
                  {row.full_name}
                </button>
              )
            }
          : column
      ),
    [columns]
  );

  const courseMap = useMemo(
    () => Object.fromEntries(courses.map((item) => [item.id, `${item.name} (${item.code})`])),
    [courses]
  );
  const yearMap = useMemo(
    () => Object.fromEntries(years.map((item) => [item.id, item.label || `Year ${item.year_number}`])),
    [years]
  );

  const selectedPermissions = selectedUser ? getEffectiveExtensions(selectedUser) : [];
  const selectedScope = selectedUser ? getEffectiveScope(selectedUser) : {};
  const allowedPermissions = selectedUser ? (PERMISSION_OPTIONS[selectedUser.role] || []) : [];
  const classScope = selectedScope.class_coordinator || {};
  const clubScope = selectedScope.club_president || {};
  const availableYears = years.filter((item) => !classScope.course_id || item.course_id === classScope.course_id);
  const availableSections = sections.filter((item) => {
    if (classScope.department_code) {
      const dep = departments.find((d) => d.code === classScope.department_code);
      if (dep && item.faculty_name) {
        const left = String(item.faculty_name).trim().toLowerCase();
        const right = String(dep.name || '').trim().toLowerCase();
        if (left && right && left !== right && !left.includes(right) && !right.includes(left)) {
          return false;
        }
      }
    }
    if (classScope.course_id && item.course_id !== classScope.course_id) return false;
    if (classScope.year_id && item.year_id !== classScope.year_id) return false;
    return true;
  });

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">Users</h1>
          <button className="btn-secondary" onClick={loadUsers}>Refresh</button>
        </div>
      </Card>

      <Card className="space-y-3">
        <button
          type="button"
          className="flex w-full items-center justify-between rounded-lg px-1 py-1 text-left"
          onClick={() => setOpenTeachers((prev) => !prev)}
        >
          <h2 className="text-lg font-semibold">Teachers ({teacherRows.length})</h2>
          {openTeachers ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {openTeachers ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <FormInput
                label="Search Teachers"
                value={teacherSearch}
                onChange={(e) => setTeacherSearch(e.target.value)}
                placeholder="Teacher name / email"
              />
            </div>
            {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
            <Table columns={clickableColumns} data={teacherRows} />
          </>
        ) : null}
      </Card>

      <Card className="space-y-3">
        <button
          type="button"
          className="flex w-full items-center justify-between rounded-lg px-1 py-1 text-left"
          onClick={() => setOpenStudents((prev) => !prev)}
        >
          <h2 className="text-lg font-semibold">Students ({studentRows.length})</h2>
          {openStudents ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {openStudents ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <FormInput
                label="Search Students"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
                placeholder="Student name / email"
              />
            </div>
            <Table columns={clickableColumns} data={studentRows} />
          </>
        ) : null}
      </Card>

      {selectedUser ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-20 bg-black/45"
            onClick={() => setSelectedUserId('')}
          />
          <div className="fixed inset-0 z-30 overflow-y-auto p-4 lg:p-8">
            <div className="mx-auto max-w-6xl">
              <Card className="space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <h2 className="text-xl font-semibold">{selectedUser.full_name}</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {selectedUser.email} | {selectedUser.role}
                    </p>
                  </div>
                  <button type="button" className="btn-secondary !p-2" onClick={() => setSelectedUserId('')}>
                    <X size={16} />
                  </button>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    className={cn('btn-secondary', selectedTab === 'details' && '!bg-brand-100 !text-brand-700')}
                    onClick={() => setSelectedTab('details')}
                  >
                    Details
                  </button>
                  <button
                    type="button"
                    className={cn('btn-secondary', selectedTab === 'permissions' && '!bg-brand-100 !text-brand-700')}
                    onClick={() => setSelectedTab('permissions')}
                  >
                    Permissions
                  </button>
                </div>

                {selectedTab === 'details' ? (
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <FormInput label="Full Name" value={selectedUser.full_name || ''} disabled />
                    <FormInput label="Email" value={selectedUser.email || ''} disabled />
                    <FormInput label="Phone" value={selectedUser.profile?.phone || ''} disabled />
                    <FormInput label="Department" value={selectedUser.profile?.department || ''} disabled />
                    <FormInput label="Designation" value={selectedUser.profile?.designation || ''} disabled />
                    <FormInput label="Organization" value={selectedUser.profile?.organization || ''} disabled />
                    <FormInput label="City" value={selectedUser.profile?.city || ''} disabled />
                    <FormInput label="State" value={selectedUser.profile?.state || ''} disabled />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center gap-2">
                      {allowedPermissions.map((permission) => (
                        <FlipButton
                          key={permission}
                          checked={selectedPermissions.includes(permission)}
                          disabled={savingIds.includes(selectedUser.id)}
                          onClick={() => toggleExtension(selectedUser, permission)}
                          label={permission}
                        />
                      ))}
                    </div>

                    {selectedUser.role === 'teacher' && selectedPermissions.includes('class_coordinator') ? (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        <FormInput
                          as="select"
                          label="Department"
                          value={classScope.department_code || ''}
                          onChange={(e) =>
                            updateClassCoordinatorScope(selectedUser, {
                              department_code: e.target.value || null,
                              class_id: null
                            })
                          }
                        >
                          <option value="">Select Department</option>
                          {departments.map((item) => (
                            <option key={item.id} value={item.code}>{item.name}</option>
                          ))}
                        </FormInput>
                        <FormInput
                          as="select"
                          label="Course"
                          value={classScope.course_id || ''}
                          onChange={(e) =>
                            updateClassCoordinatorScope(selectedUser, {
                              course_id: e.target.value || null,
                              year_id: null,
                              class_id: null
                            })
                          }
                        >
                          <option value="">Select Course</option>
                          {courses.map((item) => (
                            <option key={item.id} value={item.id}>{item.name}</option>
                          ))}
                        </FormInput>
                        <FormInput
                          as="select"
                          label="Year"
                          value={classScope.year_id || ''}
                          onChange={(e) =>
                            updateClassCoordinatorScope(selectedUser, {
                              year_id: e.target.value || null,
                              class_id: null
                            })
                          }
                        >
                          <option value="">Select Year</option>
                          {availableYears.map((item) => (
                            <option key={item.id} value={item.id}>{item.label || `Year ${item.year_number}`}</option>
                          ))}
                        </FormInput>
                        <FormInput
                          as="select"
                          label="Section"
                          value={classScope.class_id || ''}
                          onChange={(e) => {
                            const classId = e.target.value || null;
                            const classDoc = sections.find((item) => item.id === classId);
                            updateClassCoordinatorScope(selectedUser, {
                              class_id: classId,
                              course_id: classDoc?.course_id || classScope.course_id || null,
                              year_id: classDoc?.year_id || classScope.year_id || null
                            });
                          }}
                        >
                          <option value="">Select Section</option>
                          {availableSections.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.name} | {courseMap[item.course_id] || item.course_id} | {yearMap[item.year_id] || item.year_id}
                            </option>
                          ))}
                        </FormInput>
                      </div>
                    ) : null}

                    {selectedUser.role === 'student' && selectedPermissions.includes('club_president') ? (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        <FormInput
                          as="select"
                          label="Club"
                          value={clubScope.club_id || ''}
                          onChange={(e) => updateClubPresidentScope(selectedUser, { club_id: e.target.value || null })}
                        >
                          <option value="">Select Club</option>
                          {clubs.map((item) => (
                            <option key={item.id} value={item.id}>{item.name}</option>
                          ))}
                        </FormInput>
                      </div>
                    ) : null}

                    <div className="flex justify-end">
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={savingIds.includes(selectedUser.id)}
                        onClick={() => savePermissions(selectedUser)}
                      >
                        {savingIds.includes(selectedUser.id) ? 'Saving...' : 'Save Permissions'}
                      </button>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
