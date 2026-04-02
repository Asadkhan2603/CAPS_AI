import FormInput from '../FormInput';
import Modal from '../Modal';
import SearchableSelect from '../SearchableSelect';

export default function EntityFormOverlay({
  activeFormFields,
  closeFormOverlay,
  createValues,
  editingRowId,
  filterValues,
  onCreateChange,
  onSubmit,
  open,
  resolveFieldOptions,
  resolveSelectedLabel,
  rows,
  singularTitle
}) {
  return (
    <Modal
      open={open}
      title={editingRowId ? `Edit ${singularTitle}` : `Create ${singularTitle}`}
      onClose={closeFormOverlay}
      size="large"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {activeFormFields.map((field) =>
            field.type === 'switch' ? (
              <label key={field.name} className="block space-y-1">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{field.label}</span>
                <div className="flex h-11 items-center">
                  <label className="inline-flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      className="peer sr-only"
                      checked={Boolean(createValues[field.name])}
                      onChange={(e) => onCreateChange(field.name, e.target.checked)}
                    />
                    <span className="relative h-6 w-11 rounded-full bg-slate-300 transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-transform after:content-[''] peer-checked:bg-brand-500 peer-checked:after:translate-x-5 dark:bg-slate-700" />
                    <span className="text-xs text-slate-600 dark:text-slate-300">
                      {createValues[field.name] ? 'Enabled' : 'Disabled'}
                    </span>
                  </label>
                </div>
              </label>
            ) : field.type === 'select' && field.searchable ? (
              <SearchableSelect
                key={field.name}
                label={field.label}
                value={createValues[field.name]}
                loadOptions={
                  typeof field.loadOptions === 'function'
                    ? (query) =>
                        field.loadOptions({
                          query,
                          mode: 'create',
                          createValues,
                          filterValues,
                          rows
                        })
                    : undefined
                }
                options={resolveFieldOptions(field, 'create', createValues, filterValues)}
                selectedLabel={resolveSelectedLabel(field, 'create', createValues, filterValues)}
                placeholder={field.placeholder || `Search ${field.label}`}
                required={field.required}
                disabled={Boolean(field.disabledWhen?.({ createValues, filterValues, rows }))}
                allowEmpty={!field.required}
                emptyLabel={field.placeholder || `Select ${field.label}`}
                onValueChange={(nextValue) => onCreateChange(field.name, nextValue)}
              />
            ) : field.type === 'select' ? (
              <FormInput
                key={field.name}
                as="select"
                label={field.label}
                required={field.required}
                value={createValues[field.name]}
                onChange={(e) => onCreateChange(field.name, e.target.value)}
              >
                <option value="">{field.placeholder || `Select ${field.label}`}</option>
                {resolveFieldOptions(field, 'create', createValues, filterValues).map((option) => (
                  <option key={`${field.name}-${option.value}`} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </FormInput>
            ) : (
              <FormInput
                key={field.name}
                label={field.label}
                type={field.type === 'datetime' ? 'datetime-local' : field.type || 'text'}
                min={field.min}
                max={field.max}
                required={field.required}
                value={createValues[field.name]}
                placeholder={field.placeholder}
                onChange={(e) => onCreateChange(field.name, e.target.value)}
              />
            )
          )}
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={closeFormOverlay}>
            Cancel
          </button>
          <button type="submit" className="btn-primary">
            {editingRowId ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
