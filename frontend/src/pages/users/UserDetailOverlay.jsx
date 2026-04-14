import { X } from 'lucide-react';
import Card from '../../components/ui/Card';
import FormInput from '../../components/ui/FormInput';
import { useAuthorizedImage } from '../../hooks/useAuthorizedImage';
import { cn } from '../../utils/cn';

const PERMISSION_OPTIONS = {
  teacher: ['year_head', 'class_coordinator', 'club_coordinator'],
  student: ['club_president']
};

const PERMISSION_META = {
  year_head: {
    label: 'Year Head',
    description: 'Can supervise year-level academic operations and escalations.'
  },
  class_coordinator: {
    label: 'Class Coordinator',
    description: 'Can manage section-level coordination and class ownership scope.'
  },
  club_coordinator: {
    label: 'Club Coordinator',
    description: 'Can supervise club operations and activity planning support.'
  },
  club_president: {
    label: 'Club President',
    description: 'Can represent and operate leadership functions for one club.'
  }
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

export default function UserDetailOverlay({
  batches,
  clubs,
  close,
  departments,
  faculties,
  getEffectiveExtensions,
  getEffectiveScope,
  programs,
  savePermissions,
  savingIds,
  sections,
  selectedTab,
  selectedUser,
  semesters,
  setSelectedTab,
  specializations,
  toggleExtension,
  updateClassCoordinatorScope,
  updateClubPresidentScope
}) {
  if (!selectedUser) return null;

  const avatarSrc = useAuthorizedImage(selectedUser.avatar_url, selectedUser.avatar_updated_at);
  const selectedPermissions = getEffectiveExtensions(selectedUser);
  const selectedScope = getEffectiveScope(selectedUser);
  const basePermissions = selectedUser.extended_roles || [];
  const baseScope = selectedUser.role_scope || {};
  const hasPermissionDiff = hasArrayDifference(selectedPermissions, basePermissions);
  const hasScopeDiff = stableSerialize(selectedScope) !== stableSerialize(baseScope);
  const hasPendingChanges = hasPermissionDiff || hasScopeDiff;
  const allowedPermissions = PERMISSION_OPTIONS[selectedUser.role] || [];
  const classScope = selectedScope.class_coordinator || {};
  const clubScope = selectedScope.club_president || {};
  const programMap = Object.fromEntries(programs.map((item) => [item.id, item.name]));
  const semesterMap = Object.fromEntries(semesters.map((item) => [item.id, item.label]));
  const availableDepartments = departments.filter((item) => !classScope.faculty_id || item.faculty_id === classScope.faculty_id);
  const availablePrograms = programs.filter((item) => !classScope.department_id || item.department_id === classScope.department_id);
  const availableSpecializations = specializations.filter((item) => !classScope.program_id || item.program_id === classScope.program_id);
  const availableBatches = batches.filter(
    (item) =>
      (!classScope.program_id || item.program_id === classScope.program_id) &&
      (!classScope.specialization_id || item.specialization_id === classScope.specialization_id)
  );
  const availableSemesters = semesters.filter((item) => !classScope.batch_id || item.batch_id === classScope.batch_id);
  const availableSections = sections.filter((item) => {
    if (classScope.faculty_id && item.faculty_id !== classScope.faculty_id) return false;
    if (classScope.department_id && item.department_id !== classScope.department_id) return false;
    if (classScope.program_id && item.program_id !== classScope.program_id) return false;
    if (classScope.specialization_id && item.specialization_id !== classScope.specialization_id) return false;
    if (classScope.batch_id && item.batch_id !== classScope.batch_id) return false;
    if (classScope.semester_id && item.semester_id !== classScope.semester_id) return false;
    return true;
  });

  return (
    <>
      <button type="button" className="fixed inset-0 z-20 bg-black/45" onClick={close} />
      <div className="fixed inset-0 z-30 overflow-y-auto p-4 lg:p-8">
        <div className="mx-auto max-w-6xl">
          <Card className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                {avatarSrc ? (
                  <img
                    src={avatarSrc}
                    alt={`${selectedUser.full_name || 'User'} profile`}
                    className="h-14 w-14 rounded-2xl border border-slate-200 object-cover dark:border-slate-700"
                  />
                ) : (
                  <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-100 text-lg font-semibold uppercase text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                    {getNameInitials(selectedUser.full_name)}
                  </span>
                )}
                <div>
                  <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 md:text-3xl">
                    {selectedUser.full_name}
                  </h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{selectedUser.email}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-1 font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                      Role: {formatRoleLabel(selectedUser.role)}
                    </span>
                    {selectedUser.admin_type ? (
                      <span className="rounded-full border border-brand-200 bg-brand-50 px-2 py-1 font-medium text-brand-700 dark:border-brand-900/50 dark:bg-brand-900/20 dark:text-brand-300">
                        Type: {formatRoleLabel(selectedUser.admin_type)}
                      </span>
                    ) : null}
                    <span
                      className={cn(
                        'rounded-full border px-2 py-1 font-medium',
                        selectedUser.is_active === false
                          ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300'
                      )}
                    >
                      {selectedUser.is_active === false ? 'Inactive' : 'Active'}
                    </span>
                  </div>
                </div>
              </div>
              <button type="button" className="btn-secondary !p-2" onClick={close}>
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
              <div className="space-y-3">
                <div className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-800/40 sm:grid-cols-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Extended Roles</p>
                    <p className="mt-1 font-medium text-slate-800 dark:text-slate-100">
                      {selectedPermissions.length ? selectedPermissions.map(formatRoleLabel).join(', ') : 'None'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Permission Mode</p>
                    <p className="mt-1 font-medium text-slate-800 dark:text-slate-100">Role + Extension based</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Scope Status</p>
                    <p className="mt-1 font-medium text-slate-800 dark:text-slate-100">
                      {classScope.class_id || clubScope.club_id ? 'Scoped assignment configured' : 'No scoped assignment'}
                    </p>
                  </div>
                </div>
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
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-2xl border border-brand-200 bg-brand-50/70 px-4 py-3 text-sm text-brand-800 dark:border-brand-900/40 dark:bg-brand-950/20 dark:text-brand-200">
                  <p className="font-semibold">Extended Role Upgrade</p>
                  <p className="mt-1 text-xs">
                    Upgrade permissions by enabling one or more extended roles and setting the required scope.
                  </p>
                </div>

                {allowedPermissions.length ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {allowedPermissions.map((permission) => {
                      const meta = PERMISSION_META[permission] || {
                        label: formatRoleLabel(permission),
                        description: 'Additional access extension for this user role.'
                      };
                      const enabled = selectedPermissions.includes(permission);
                      return (
                        <div
                          key={permission}
                          className={cn(
                            'rounded-2xl border p-3',
                            enabled
                              ? 'border-brand-300 bg-brand-50/60 dark:border-brand-800/50 dark:bg-brand-950/20'
                              : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
                          )}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{meta.label}</p>
                              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{meta.description}</p>
                            </div>
                            <FlipButton
                              checked={enabled}
                              disabled={savingIds.includes(selectedUser.id)}
                              onClick={() => toggleExtension(selectedUser, permission)}
                              label={enabled ? 'Enabled' : 'Enable'}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                    This role does not support upgrade permissions.
                  </div>
                )}

                {hasPendingChanges ? (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                    You have unsaved permission changes.
                  </div>
                ) : null}

                {selectedUser.role === 'teacher' && selectedPermissions.includes('class_coordinator') ? (
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <FormInput as="select" label="Faculty" value={classScope.faculty_id || ''} onChange={(e) => updateClassCoordinatorScope(selectedUser, { faculty_id: e.target.value || null, department_id: null, program_id: null, specialization_id: null, batch_id: null, semester_id: null, class_id: null })}>
                      <option value="">Select Faculty</option>
                      {faculties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </FormInput>
                    <FormInput as="select" label="Department" value={classScope.department_id || ''} onChange={(e) => updateClassCoordinatorScope(selectedUser, { department_id: e.target.value || null, program_id: null, specialization_id: null, batch_id: null, semester_id: null, class_id: null })}>
                      <option value="">Select Department</option>
                      {availableDepartments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </FormInput>
                    <FormInput as="select" label="Program" value={classScope.program_id || ''} onChange={(e) => updateClassCoordinatorScope(selectedUser, { program_id: e.target.value || null, specialization_id: null, batch_id: null, semester_id: null, class_id: null })}>
                      <option value="">Select Program</option>
                      {availablePrograms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </FormInput>
                    <FormInput as="select" label="Specialization" value={classScope.specialization_id || ''} onChange={(e) => updateClassCoordinatorScope(selectedUser, { specialization_id: e.target.value || null, batch_id: null, semester_id: null, class_id: null })}>
                      <option value="">Select Specialization</option>
                      {availableSpecializations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </FormInput>
                    <FormInput as="select" label="Batch" value={classScope.batch_id || ''} onChange={(e) => updateClassCoordinatorScope(selectedUser, { batch_id: e.target.value || null, semester_id: null, class_id: null })}>
                      <option value="">Select Batch</option>
                      {availableBatches.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </FormInput>
                    <FormInput as="select" label="Semester" value={classScope.semester_id || ''} onChange={(e) => updateClassCoordinatorScope(selectedUser, { semester_id: e.target.value || null, class_id: null })}>
                      <option value="">Select Semester</option>
                      {availableSemesters.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
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
                          faculty_id: classDoc?.faculty_id || classScope.faculty_id || null,
                          department_id: classDoc?.department_id || classScope.department_id || null,
                          program_id: classDoc?.program_id || classScope.program_id || null,
                          specialization_id: classDoc?.specialization_id || classScope.specialization_id || null,
                          batch_id: classDoc?.batch_id || classScope.batch_id || null,
                          semester_id: classDoc?.semester_id || classScope.semester_id || null
                        });
                      }}
                    >
                      <option value="">Select Section</option>
                      {availableSections.map((item) => (
                        <option key={item.id} value={item.id}>{item.name} | {programMap[item.program_id] || '-'} | {semesters.find((semester) => semester.id === item.semester_id)?.label || '-'}</option>
                      ))}
                    </FormInput>
                  </div>
                ) : null}

                {selectedUser.role === 'student' && selectedPermissions.includes('club_president') ? (
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <FormInput as="select" label="Club" value={clubScope.club_id || ''} onChange={(e) => updateClubPresidentScope(selectedUser, { club_id: e.target.value || null })}>
                      <option value="">Select Club</option>
                      {clubs.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </FormInput>
                  </div>
                ) : null}

                <div className="flex justify-end">
                  <button type="button" className="btn-primary" disabled={savingIds.includes(selectedUser.id)} onClick={() => savePermissions(selectedUser)}>
                    {savingIds.includes(selectedUser.id) ? 'Saving...' : 'Save Permissions'}
                  </button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

function hasArrayDifference(left = [], right = []) {
  if (left.length !== right.length) return true;
  const leftSorted = [...left].sort();
  const rightSorted = [...right].sort();
  return leftSorted.some((item, index) => item !== rightSorted[index]);
}

function stableSerialize(value) {
  return JSON.stringify(sortDeep(value));
}

function sortDeep(value) {
  if (Array.isArray(value)) {
    return value.map(sortDeep);
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        acc[key] = sortDeep(value[key]);
        return acc;
      }, {});
  }
  return value ?? null;
}

function formatRoleLabel(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
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
