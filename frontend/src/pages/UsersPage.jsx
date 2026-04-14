import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Table from '../components/ui/Table';
import { useAuthorizedImage } from '../hooks/useAuthorizedImage';
import { useToast } from '../hooks/useToast';
import UserDetailOverlay from './users/UserDetailOverlay';
import { useUsersPageData } from './users/useUsersPageData';

export default function UsersPage() {
  const { pushToast } = useToast();
  const [adminSearch, setAdminSearch] = useState('');
  const [openAdmins, setOpenAdmins] = useState(true);
  const [teacherSearch, setTeacherSearch] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [openTeachers, setOpenTeachers] = useState(true);
  const [openStudents, setOpenStudents] = useState(true);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedTab, setSelectedTab] = useState('details');
  const {
    batches,
    clubs,
    departments,
    error,
    faculties,
    getEffectiveExtensions,
    getEffectiveScope,
    loading,
    loadUsers,
    programs,
    rows,
    savePermissions,
    savingIds,
    sections,
    semesters,
    specializations,
    toggleExtension,
    updateClassCoordinatorScope,
    updateClubPresidentScope
  } = useUsersPageData({ pushToast });

  const selectedUser = useMemo(
    () => rows.find((item) => item.id === selectedUserId) || null,
    [rows, selectedUserId]
  );

  useEffect(() => {
    if (selectedUser) {
      setSelectedTab('details');
    }
  }, [selectedUserId]);

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

  const adminRows = useMemo(() => {
    const needle = adminSearch.trim().toLowerCase();
    const base = rows.filter((row) => row.role === 'admin');
    if (!needle) return base;
    return base.filter(
      (row) =>
        row.full_name?.toLowerCase().includes(needle) ||
        row.email?.toLowerCase().includes(needle) ||
        String(row.admin_type || '').toLowerCase().includes(needle)
    );
  }, [rows, adminSearch]);

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
    [getEffectiveExtensions]
  );

  const adminColumns = useMemo(
    () => [
      {
        key: 'full_name',
        label: 'Admin',
        render: (row) => (
          <UserNameButton row={row} onClick={() => setSelectedUserId(row.id)} />
        )
      },
      { key: 'email', label: 'Email' },
      {
        key: 'admin_details',
        label: 'Admin Details',
        render: (row) => <AdminDetailsCell row={row} />
      }
    ],
    []
  );

  const clickableColumns = useMemo(
    () =>
      columns.map((column) =>
        column.key === 'full_name'
          ? {
              ...column,
              render: (row) => (
                <UserNameButton row={row} onClick={() => setSelectedUserId(row.id)} />
              )
            }
          : column
      ),
    [columns]
  );

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
          onClick={() => setOpenAdmins((prev) => !prev)}
        >
          <h2 className="text-lg font-semibold">Admins ({adminRows.length})</h2>
          {openAdmins ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {openAdmins ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <FormInput
                label="Search Admins"
                value={adminSearch}
                onChange={(e) => setAdminSearch(e.target.value)}
                placeholder="Admin name / email / type"
              />
            </div>
            {loading ? <p className="text-sm text-slate-500">Loading...</p> : null}
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
            <Table columns={adminColumns} data={adminRows} />
          </>
        ) : null}
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

      <UserDetailOverlay
        batches={batches}
        clubs={clubs}
        close={() => setSelectedUserId('')}
        departments={departments}
        faculties={faculties}
        getEffectiveExtensions={getEffectiveExtensions}
        getEffectiveScope={getEffectiveScope}
        programs={programs}
        savePermissions={savePermissions}
        savingIds={savingIds}
        sections={sections}
        selectedTab={selectedTab}
        selectedUser={selectedUser}
        semesters={semesters}
        setSelectedTab={setSelectedTab}
        specializations={specializations}
        toggleExtension={toggleExtension}
        updateClassCoordinatorScope={updateClassCoordinatorScope}
        updateClubPresidentScope={updateClubPresidentScope}
      />
    </div>
  );
}

function AdminDetailsCell({ row }) {
  const createdAt = row.created_at ? new Date(row.created_at).toLocaleString() : '-';
  return (
    <div className="space-y-1 text-xs">
      <div className="font-medium text-slate-700 dark:text-slate-200">Type: {row.admin_type || '-'}</div>
      <div className="text-slate-500 dark:text-slate-400">Status: {row.is_active === false ? 'inactive' : 'active'}</div>
      <div className="text-slate-500 dark:text-slate-400">Created: {createdAt}</div>
    </div>
  );
}

function UserNameButton({ row, onClick }) {
  const avatarSrc = useAuthorizedImage(row.avatar_url, row.avatar_updated_at);
  const initials = getNameInitials(row.full_name);

  return (
    <button
      type="button"
      className="inline-flex items-center gap-2 text-left font-medium text-brand-600 underline-offset-2 hover:underline dark:text-brand-300"
      onClick={onClick}
    >
      {avatarSrc ? (
        <img
          src={avatarSrc}
          alt={`${row.full_name || 'User'} profile`}
          className="h-7 w-7 rounded-full border border-slate-200 object-cover dark:border-slate-700"
        />
      ) : (
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-slate-100 text-[10px] font-semibold uppercase text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          {initials}
        </span>
      )}
      <span>{row.full_name}</span>
    </button>
  );
}

function getNameInitials(name) {
  const words = String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  if (!words.length) return 'U';
  return words.map((word) => word[0]).join('').toUpperCase();
}
