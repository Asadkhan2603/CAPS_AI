import FormInput from '../../components/ui/FormInput';
import Modal from '../../components/ui/Modal';
import SearchableSelect from '../../components/ui/SearchableSelect';

export default function BatchFormModal({
  closeModal,
  editingBatch,
  filteredSpecializationOptions,
  formValues,
  loadProgramOptions,
  loadSpecializationOptions,
  modalOpen,
  onSubmit,
  programOptions,
  saving,
  selectedProgram,
  selectedSpecialization,
  setIdentityTouched,
  suggestedIdentity,
  updateFormValue
}) {
  return (
    <Modal open={modalOpen} title={editingBatch ? 'Edit Batch' : 'Create Batch'} onClose={closeModal}>
      <form className="space-y-4" onSubmit={onSubmit}>
        <SearchableSelect
          label="Program"
          value={formValues.program_id}
          options={programOptions}
          loadOptions={loadProgramOptions}
          selectedLabel={selectedProgram ? `${selectedProgram.name} (${selectedProgram.code})` : ''}
          placeholder="Select program"
          onValueChange={(value) => {
            updateFormValue('program_id', value);
            updateFormValue('specialization_id', '');
          }}
          required
        />

        <SearchableSelect
          label="Specialization"
          value={formValues.specialization_id}
          options={filteredSpecializationOptions}
          loadOptions={(query) => loadSpecializationOptions(query, formValues.program_id)}
          selectedLabel={selectedSpecialization ? `${selectedSpecialization.name} (${selectedSpecialization.code})` : ''}
          allowEmpty
          disabled={!formValues.program_id}
          emptyLabel="Program-level batch"
          placeholder={formValues.program_id ? 'Select specialization' : 'Select program first'}
          onValueChange={(value) => updateFormValue('specialization_id', value)}
        />

        <div className="grid gap-4 md:grid-cols-2">
          <FormInput
            label="Start Year / Join Year"
            type="number"
            min="2000"
            max="2100"
            value={formValues.start_year}
            placeholder="2022"
            onChange={(event) => updateFormValue('start_year', event.target.value)}
          />
          <FormInput
            label="End Year / Pass-out Year"
            type="number"
            min="2000"
            max="2100"
            value={formValues.end_year}
            placeholder="2026 for Aug 2022 to May 2026"
            onChange={(event) => {
              setIdentityTouched((prev) => ({ ...prev, endYear: true }));
              updateFormValue('end_year', event.target.value);
            }}
          />
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
          Suggested identity: <span className="font-semibold">{suggestedIdentity.name || 'Batch 2022-2026'}</span> |{' '}
          <span className="font-semibold">{suggestedIdentity.code || 'B.Sc.-B22-26'}</span>
        </div>

        <FormInput
          label="Batch Name"
          value={formValues.name}
          placeholder="Batch 2022-2026"
          onChange={(event) => {
            setIdentityTouched((prev) => ({ ...prev, name: true }));
            updateFormValue('name', event.target.value);
          }}
          required
        />

        <FormInput
          label="Batch Code"
          value={formValues.code}
          placeholder="B.Sc.-B22-26"
          onChange={(event) => {
            setIdentityTouched((prev) => ({ ...prev, code: true }));
            updateFormValue('code', event.target.value);
          }}
          required
        />

        {editingBatch ? (
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={Boolean(formValues.is_active)}
              onChange={(event) => updateFormValue('is_active', event.target.checked)}
            />
            Batch is active
          </label>
        ) : null}

        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={closeModal} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : editingBatch ? 'Update Batch' : 'Create Batch'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
