import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Modal from '../components/ui/Modal';
import SearchableSelect from '../components/ui/SearchableSelect';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/apiClient';
import { formatApiError } from '../utils/apiError';

const PAGE_SIZE = 100;
const MAX_PAGES = 20;

function buildBatchCodeSuffix(startYear, endYear) {
  if (!startYear || !endYear) return '';
  return `B${String(startYear).slice(-2)}-${String(endYear).slice(-2)}`;
}

function buildProgramBatchPrefix(program) {
  if (!program) return '';
  const rawName = String(program.name || '')
    .split(/\s*(?:\(|-)\s*/, 1)[0]
    .trim();
  if (rawName) return rawName;
  return String(program.code || '').trim().toUpperCase();
}

function buildSuggestedBatchIdentity(program, startYear, endYear) {
  if (!startYear || !endYear) {
    return { name: '', code: '' };
  }

  const prefix = buildProgramBatchPrefix(program);
  const suffix = buildBatchCodeSuffix(startYear, endYear);
  return {
    name: `Batch ${startYear}-${endYear}`,
    code: prefix ? `${prefix}-${suffix}` : suffix
  };
}

function normalizeYearInput(value) {
  if (value === '' || value === null || value === undefined) return '';
  return String(value);
}

async function listAll(path, params = {}) {
  const rows = [];
  for (let page = 0; page < MAX_PAGES; page += 1) {
    const response = await apiClient.get(path, {
      params: { ...params, skip: page * PAGE_SIZE, limit: PAGE_SIZE }
    });
    const items = Array.isArray(response.data) ? response.data : [];
    rows.push(...items);
    if (items.length < PAGE_SIZE) break;
  }
  return rows;
}

async function listAllBatches() {
  const [activeRows, inactiveRows] = await Promise.all([
    listAll('/batches/', { is_active: true }),
    listAll('/batches/', { is_active: false })
  ]);
  const merged = new Map();
  [...activeRows, ...inactiveRows].forEach((item) => {
    if (item?.id) {
      merged.set(item.id, item);
    }
  });
  return Array.from(merged.values());
}

function sortBatches(rows) {
  return [...rows].sort((left, right) => {
    const leftStart = Number(left.start_year || 0);
    const rightStart = Number(right.start_year || 0);
    if (leftStart !== rightStart) return leftStart - rightStart;
    return String(left.code || '').localeCompare(String(right.code || ''));
  });
}

function createEmptyForm() {
  return {
    program_id: '',
    specialization_id: '',
    name: '',
    code: '',
    start_year: '',
    end_year: '',
    is_active: true
  };
}

export default function BatchesPage() {
  const { pushToast } = useToast();
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [programFilter, setProgramFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [expandedProgramId, setExpandedProgramId] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBatch, setEditingBatch] = useState(null);
  const [formValues, setFormValues] = useState(createEmptyForm());
  const [identityTouched, setIdentityTouched] = useState({ name: false, code: false, endYear: false });
  const [error, setError] = useState('');

  async function loadPageData() {
    setLoading(true);
    setError('');
    try {
      const [programRows, specializationRows, batchRows] = await Promise.all([
        listAll('/programs/', { is_active: true }),
        listAll('/specializations/', { is_active: true }),
        listAllBatches()
      ]);
      setPrograms(programRows);
      setSpecializations(specializationRows);
      setBatches(batchRows);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load batches');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPageData();
  }, []);

  const programMap = useMemo(() => Object.fromEntries(programs.map((item) => [item.id, item])), [programs]);
  const specializationMap = useMemo(() => Object.fromEntries(specializations.map((item) => [item.id, item])), [specializations]);

  const programOptions = useMemo(
    () => programs.map((program) => ({ value: program.id, label: `${program.name} (${program.code})` })),
    [programs]
  );

  const specializationOptions = useMemo(
    () =>
      specializations.map((item) => ({
        value: item.id,
        label: `${item.name} (${item.code})`,
        program_id: item.program_id
      })),
    [specializations]
  );

  const visibleGroups = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    const grouped = new Map();

    batches.forEach((batch) => {
      const program = programMap[batch.program_id];
      if (!program) return;
      if (programFilter && batch.program_id !== programFilter) return;
      if (!showInactive && batch.is_active === false) return;

      const searchText = [
        batch.name,
        batch.code,
        program.name,
        program.code,
        specializationMap[batch.specialization_id]?.name,
        batch.academic_span_label,
        batch.university_code,
        batch.university_name
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      if (normalizedQuery && !searchText.includes(normalizedQuery)) return;

      if (!grouped.has(program.id)) {
        grouped.set(program.id, { program, batches: [] });
      }
      grouped.get(program.id).batches.push(batch);
    });

    return Array.from(grouped.values())
      .map((group) => ({
        ...group,
        batches: sortBatches(group.batches)
      }))
      .sort((left, right) => String(left.program.name || '').localeCompare(String(right.program.name || '')));
  }, [batches, programFilter, programMap, searchQuery, showInactive, specializationMap]);

  useEffect(() => {
    if (!visibleGroups.length) {
      setExpandedProgramId(null);
      return;
    }
    if (expandedProgramId === null) {
      setExpandedProgramId(visibleGroups[0].program.id);
      return;
    }
    const stillVisible = visibleGroups.some((group) => group.program.id === expandedProgramId);
    if (!stillVisible && expandedProgramId !== '') {
      setExpandedProgramId(visibleGroups[0].program.id);
    }
  }, [expandedProgramId, visibleGroups]);

  const selectedProgram = programMap[formValues.program_id] || null;
  const selectedProgramDuration = Number(selectedProgram?.duration_years || 0);
  const startYearValue = Number(formValues.start_year || 0);
  const endYearValue = Number(formValues.end_year || 0);
  const suggestedIdentity = useMemo(
    () =>
      buildSuggestedBatchIdentity(
        selectedProgram,
        startYearValue || null,
        endYearValue || null
      ),
    [selectedProgram, startYearValue, endYearValue]
  );

  useEffect(() => {
    if (!modalOpen || editingBatch) return;
    if (!selectedProgram || !startYearValue || identityTouched.endYear) return;

    const suggestedEndYear = startYearValue + Math.max(selectedProgramDuration || 4, 1);
    setFormValues((prev) => {
      const nextEndYear = String(suggestedEndYear);
      if (String(prev.end_year || '') === nextEndYear) return prev;
      return { ...prev, end_year: nextEndYear };
    });
  }, [editingBatch, identityTouched.endYear, modalOpen, selectedProgram, selectedProgramDuration, startYearValue]);

  useEffect(() => {
    if (!modalOpen || editingBatch) return;
    if (!suggestedIdentity.name || !suggestedIdentity.code) return;

    setFormValues((prev) => {
      let changed = false;
      const next = { ...prev };

      if (!identityTouched.name || !String(prev.name || '').trim()) {
        if (next.name !== suggestedIdentity.name) {
          next.name = suggestedIdentity.name;
          changed = true;
        }
      }

      if (!identityTouched.code || !String(prev.code || '').trim()) {
        if (next.code !== suggestedIdentity.code) {
          next.code = suggestedIdentity.code;
          changed = true;
        }
      }

      return changed ? next : prev;
    });
  }, [editingBatch, identityTouched.code, identityTouched.name, modalOpen, suggestedIdentity]);

  const filteredSpecializationOptions = useMemo(
    () => specializationOptions.filter((item) => item.program_id === formValues.program_id),
    [formValues.program_id, specializationOptions]
  );

  function openCreateModal() {
    setEditingBatch(null);
    setFormValues(createEmptyForm());
    setIdentityTouched({ name: false, code: false, endYear: false });
    setModalOpen(true);
  }

  function openEditModal(batch) {
    setEditingBatch(batch);
    setFormValues({
      program_id: batch.program_id || '',
      specialization_id: batch.specialization_id || '',
      name: batch.name || '',
      code: batch.code || '',
      start_year: normalizeYearInput(batch.start_year),
      end_year: normalizeYearInput(batch.end_year),
      is_active: batch.is_active !== false
    });
    setIdentityTouched({ name: true, code: true, endYear: true });
    setModalOpen(true);
  }

  function closeModal() {
    if (saving) return;
    setModalOpen(false);
    setEditingBatch(null);
  }

  function updateFormValue(field, value) {
    setFormValues((prev) => ({ ...prev, [field]: value }));
  }

  async function submitForm(event) {
    event.preventDefault();
    if (!formValues.program_id) {
      pushToast({ title: 'Invalid data', description: 'Program is required.', variant: 'error' });
      return;
    }
    if (!String(formValues.name || '').trim()) {
      pushToast({ title: 'Invalid data', description: 'Batch name is required.', variant: 'error' });
      return;
    }
    if (!String(formValues.code || '').trim()) {
      pushToast({ title: 'Invalid data', description: 'Batch code is required.', variant: 'error' });
      return;
    }

    const payload = {
      program_id: formValues.program_id,
      specialization_id: formValues.specialization_id || null,
      name: String(formValues.name || '').trim(),
      code: String(formValues.code || '').trim(),
      start_year: formValues.start_year ? Number(formValues.start_year) : null,
      end_year: formValues.end_year ? Number(formValues.end_year) : null
    };

    if (editingBatch) {
      payload.is_active = Boolean(formValues.is_active);
    }

    setSaving(true);
    try {
      if (editingBatch) {
        await apiClient.put(`/batches/${editingBatch.id}`, payload);
      } else {
        await apiClient.post('/batches/', payload);
      }
      pushToast({
        title: editingBatch ? 'Batch updated' : 'Batch created',
        description: editingBatch
          ? 'The batch has been updated successfully.'
          : 'The batch has been created successfully.',
        variant: 'success'
      });
      setModalOpen(false);
      setEditingBatch(null);
      await loadPageData();
      setExpandedProgramId(payload.program_id);
    } catch (err) {
      const message = formatApiError(err, editingBatch ? 'Failed to update batch' : 'Failed to create batch');
      pushToast({ title: 'Save failed', description: message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  }

  async function deleteBatch(batch) {
    if (!window.confirm(`Archive ${batch.name} (${batch.code})?`)) return;

    try {
      await apiClient.delete(`/batches/${batch.id}`);
      pushToast({
        title: 'Batch archived',
        description: `${batch.name} has been archived.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      const message = formatApiError(err, 'Failed to archive batch');
      pushToast({ title: 'Archive failed', description: message, variant: 'error' });
    }
  }

  async function onSeedBatches() {
    setSyncing(true);
    try {
      const response = await apiClient.post('/programs/seed-batches');
      pushToast({
        title: 'Batches synced',
        description: `${response.data?.batch_count ?? 0} batches ensured across ${response.data?.program_count ?? 0} programs.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      const detail = formatApiError(err, 'Failed to sync program batches');
      pushToast({ title: 'Sync failed', description: detail, variant: 'error' });
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-5 page-fade">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm text-sky-950 dark:border-sky-900/50 dark:bg-sky-950/30 dark:text-sky-100">
        <div className="space-y-1">
          <p className="font-semibold">Batch spans follow join year to pass-out year.</p>
          <p>
            For the Indian academic cycle, an August 2022 intake finishing in May 2026 remains a 4-year batch labeled
            <span className="font-semibold"> 2022-2026</span>. Auto-generated codes now use the course prefix, for example
            <span className="font-semibold"> B.Sc.-B22-26</span>.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary" onClick={loadPageData} disabled={loading}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button type="button" className="btn-secondary" onClick={onSeedBatches} disabled={syncing}>
            <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Syncing...' : 'Sync Program Batches'}
          </button>
          <button type="button" className="btn-primary" onClick={openCreateModal}>
            <Plus size={16} /> Add Batch
          </button>
        </div>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[260px] flex-1">
            <SearchableSelect
              label="Program"
              value={programFilter}
              options={programOptions}
              allowEmpty
              emptyLabel="All Programs"
              placeholder="Filter by program"
              onValueChange={setProgramFilter}
            />
          </div>
          <div className="min-w-[240px] flex-1">
            <FormInput
              label="Search"
              value={searchQuery}
              placeholder="Search by batch, code, specialization, university"
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-3 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
            />
            Show archived batches
          </label>
        </div>

        {error ? <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p> : null}

        {!loading && visibleGroups.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
            No batches matched the current filters.
          </div>
        ) : null}

        <div className="space-y-3">
          {visibleGroups.map((group) => {
            const expanded = expandedProgramId === group.program.id;
            const programPrefix = buildProgramBatchPrefix(group.program);

            return (
              <div key={group.program.id} className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 bg-white px-4 py-4 text-left hover:bg-slate-50 dark:bg-slate-950 dark:hover:bg-slate-900"
                  onClick={() => setExpandedProgramId(expanded ? '' : group.program.id)}
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{group.program.name}</h2>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        {group.program.code}
                      </span>
                      <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 dark:bg-brand-950/40 dark:text-brand-200">
                        {group.batches.length} batch{group.batches.length === 1 ? '' : 'es'}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      Course prefix: {programPrefix || '-'} • {group.program.duration_years || 4} year course
                    </p>
                  </div>
                  {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                </button>

                {expanded ? (
                  <div className="border-t border-slate-200 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-950/60">
                    <div className="hidden grid-cols-[minmax(0,1.2fr)_170px_180px_140px_130px_100px_110px] gap-3 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 md:grid dark:text-slate-400">
                      <span>Batch</span>
                      <span>Code</span>
                      <span>Specialization</span>
                      <span>Academic Span</span>
                      <span>University</span>
                      <span>Status</span>
                      <span className="text-right">Actions</span>
                    </div>

                    <div className="divide-y divide-slate-200 dark:divide-slate-800">
                      {group.batches.map((batch) => {
                        const specialization = specializationMap[batch.specialization_id];
                        const universityLabel = batch.university_code || batch.university_name || '-';
                        return (
                          <div key={batch.id} className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(0,1.2fr)_170px_180px_140px_130px_100px_110px] md:items-center">
                            <div>
                              <p className="font-semibold text-slate-900 dark:text-white">{batch.name}</p>
                              <p className="text-sm text-slate-500 dark:text-slate-400">
                                Start {batch.start_year || '-'} • End {batch.end_year || '-'}
                              </p>
                            </div>
                            <div className="text-sm font-medium text-slate-700 dark:text-slate-200">{batch.code || '-'}</div>
                            <div className="text-sm text-slate-600 dark:text-slate-300">{specialization?.name || '-'}</div>
                            <div className="text-sm text-slate-600 dark:text-slate-300">{batch.academic_span_label || '-'}</div>
                            <div className="text-sm text-slate-600 dark:text-slate-300">{universityLabel}</div>
                            <div>
                              <span
                                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                  batch.is_active === false
                                    ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200'
                                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200'
                                }`}
                              >
                                {batch.is_active === false ? 'Archived' : 'Active'}
                              </span>
                            </div>
                            <div className="flex justify-end gap-2">
                              <button type="button" className="btn-secondary !p-2" onClick={() => openEditModal(batch)} title="Edit batch">
                                <Pencil size={16} />
                              </button>
                              {batch.is_active === false ? null : (
                                <button
                                  type="button"
                                  className="btn-secondary !p-2 !text-rose-600"
                                  onClick={() => deleteBatch(batch)}
                                  title="Archive batch"
                                >
                                  <Trash2 size={16} />
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </Card>

      <Modal open={modalOpen} title={editingBatch ? 'Edit Batch' : 'Create Batch'} onClose={closeModal}>
        <form className="space-y-4" onSubmit={submitForm}>
          <SearchableSelect
            label="Program"
            value={formValues.program_id}
            options={programOptions}
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
            allowEmpty
            emptyLabel="No specialization"
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
            Suggested identity: <span className="font-semibold">{suggestedIdentity.name || 'Batch 2022-2026'}</span> •{' '}
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
    </div>
  );
}

