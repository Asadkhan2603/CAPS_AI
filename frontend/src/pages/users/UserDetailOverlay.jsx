import { X } from 'lucide-react';
import Card from '../../components/ui/Card';
import FormInput from '../../components/ui/FormInput';
import { cn } from '../../utils/cn';

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

  const selectedPermissions = getEffectiveExtensions(selectedUser);
  const selectedScope = getEffectiveScope(selectedUser);
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
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="text-xl font-semibold">{selectedUser.full_name}</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {selectedUser.email} | {selectedUser.role}
                </p>
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
