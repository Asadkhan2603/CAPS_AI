import FormInput from '../FormInput';
import Modal from '../Modal';
import SearchableSelect from '../SearchableSelect';

export default function EntitySearchOverlay({
  closeSearchOverlay,
  createValues,
  fields,
  filterValues,
  onSearchDraftChange,
  open,
  resolveFieldOptions,
  resolveSelectedLabel,
  rows,
  title,
  applyFilters,
  resetFilters
}) {
  return (
    <Modal open={open} title={`Search ${title}`} onClose={closeSearchOverlay} size="large">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {fields.map((field) =>
            field.type === 'switch' ? (
              <label key={field.name} className="block space-y-1">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{field.label}</span>
                <button
                  type="button"
                  className="inline-flex h-11 min-w-[8.5rem] items-center justify-center rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                  onClick={() => {
                    const current = filterValues[field.name];
                    const next = current === null ? true : current === true ? false : null;
                    onSearchDraftChange(field.name, next);
                  }}
                >
                  {filterValues[field.name] === null ? 'Any' : filterValues[field.name] ? 'On' : 'Off'}
                </button>
              </label>
            ) : field.type === 'select' && field.searchable ? (
              <SearchableSelect
                key={field.name}
                label={field.label}
                value={filterValues[field.name]}
                loadOptions={
                  typeof field.loadOptions === 'function'
                    ? (query) =>
                        field.loadOptions({
                          query,
                          mode: 'filter',
                          createValues,
                          filterValues,
                          rows
                        })
                    : undefined
                }
                options={resolveFieldOptions(field, 'filter', createValues, filterValues)}
                selectedLabel={resolveSelectedLabel(field, 'filter', createValues, filterValues)}
                placeholder={field.placeholder || `Search ${field.label}`}
                allowEmpty
                emptyLabel={field.placeholder || `All ${field.label}`}
                onValueChange={(nextValue) => onSearchDraftChange(field.name, nextValue)}
              />
            ) : field.type === 'select' ? (
              <FormInput
                key={field.name}
                as="select"
                label={field.label}
                value={filterValues[field.name]}
                onChange={(e) => onSearchDraftChange(field.name, e.target.value)}
              >
                <option value="">{field.placeholder || `All ${field.label}`}</option>
                {resolveFieldOptions(field, 'filter', createValues, filterValues).map((option) => (
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
                value={filterValues[field.name]}
                placeholder={field.placeholder}
                onChange={(e) => onSearchDraftChange(field.name, e.target.value)}
              />
            )
          )}
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={closeSearchOverlay}>
            Close
          </button>
          <button type="button" className="btn-secondary" onClick={resetFilters}>
            Reset
          </button>
          <button type="button" className="btn-primary" onClick={applyFilters}>
            Apply
          </button>
        </div>
      </div>
    </Modal>
  );
}
