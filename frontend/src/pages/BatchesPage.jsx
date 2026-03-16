import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import Modal from '../components/ui/Modal';
import SearchableSelect from '../components/ui/SearchableSelect';
import { PROGRAM_DURATION_TO_SEMESTERS } from '../constants/academicHierarchy';
import { useToast } from '../hooks/useToast';
import { apiClient } from '../services/apiClient';
import { searchLookupOptions } from '../services/paginatedLookups';
import { formatApiError } from '../utils/apiError';

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

function buildSpecializationBatchPrefix(program, specialization) {
  const programPrefix = buildProgramBatchPrefix(program);
  const specializationCode = String(specialization?.code || '').trim().toUpperCase();
  return [programPrefix, specializationCode].filter(Boolean).join('-');
}

function buildSuggestedBatchIdentity(program, specialization, startYear, endYear) {
  if (!startYear || !endYear) {
    return { name: '', code: '' };
  }

  const prefix = buildSpecializationBatchPrefix(program, specialization);
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
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(50);

  function mergeById(setter, rows) {
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

  async function hydrateBatchRelations(batchRows) {
    const programIds = Array.from(new Set((batchRows || []).map((item) => item.program_id).filter(Boolean)));
    const specializationIds = Array.from(new Set((batchRows || []).map((item) => item.specialization_id).filter(Boolean)));

    const knownProgramIds = new Set(programs.map((item) => item.id));
    const knownSpecializationIds = new Set(specializations.map((item) => item.id));

    const missingProgramIds = programIds.filter((id) => !knownProgramIds.has(id));
    const missingSpecializationIds = specializationIds.filter((id) => !knownSpecializationIds.has(id));

    const [programResponses, specializationResponses] = await Promise.all([
      Promise.allSettled(missingProgramIds.map((id) => apiClient.get(`/programs/${id}`))),
      Promise.allSettled(missingSpecializationIds.map((id) => apiClient.get(`/specializations/${id}`)))
    ]);

    mergeById(
      setPrograms,
      programResponses
        .filter((result) => result.status === 'fulfilled')
        .map((result) => result.value.data)
    );
    mergeById(
      setSpecializations,
      specializationResponses
        .filter((result) => result.status === 'fulfilled')
        .map((result) => result.value.data)
    );
  }

  async function loadPageData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/batches/', {
        params: {
          skip,
          limit,
          q: searchQuery || undefined,
          program_id: programFilter || undefined,
          is_active: showInactive ? undefined : true
        }
      });
      const batchRows = Array.isArray(response.data) ? response.data : [];
      setBatches(batchRows);
      await hydrateBatchRelations(batchRows);
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
  }, [limit, programFilter, searchQuery, showInactive, skip]);

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
        grouped.set(program.id, { program, specializationGroups: new Map() });
      }

      const specializationKey = batch.specialization_id || '__unassigned__';
      const specialization =
        specializationMap[batch.specialization_id] || {
          id: specializationKey,
          name: 'Program-level Batch',
          code: ''
        };

      const programGroup = grouped.get(program.id);
      if (!programGroup.specializationGroups.has(specializationKey)) {
        programGroup.specializationGroups.set(specializationKey, {
          specialization,
          batches: []
        });
      }
      programGroup.specializationGroups.get(specializationKey).batches.push(batch);
    });

    return Array.from(grouped.values())
      .map((group) => ({
        ...group,
        specializationGroups: Array.from(group.specializationGroups.values())
          .map((specializationGroup) => ({
            ...specializationGroup,
            batches: sortBatches(specializationGroup.batches)
          }))
          .sort((left, right) =>
            String(left.specialization.name || '').localeCompare(String(right.specialization.name || ''))
          )
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
  const selectedSpecialization = specializationMap[formValues.specialization_id] || null;
  const selectedProgramDuration = Number(selectedProgram?.duration_years || 0);
  const startYearValue = Number(formValues.start_year || 0);
  const endYearValue = Number(formValues.end_year || 0);
  const suggestedIdentity = useMemo(
    () =>
      buildSuggestedBatchIdentity(
        selectedProgram,
        selectedSpecialization,
        startYearValue || null,
        endYearValue || null
      ),
    [selectedProgram, selectedSpecialization, startYearValue, endYearValue]
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

  async function loadProgramOptions(query) {
    const options = await searchLookupOptions({
      path: '/programs/',
      q: query,
      params: { is_active: true },
      mapOption: (item) => ({ value: item.id, label: `${item.name} (${item.code})`, name: item.name, code: item.code })
    });
    mergeById(setPrograms, options.map((item) => ({ id: item.value, name: item.name, code: item.code })));
    return options;
  }

  async function loadSpecializationOptions(query) {
    if (!formValues.program_id) return [];
    const options = await searchLookupOptions({
      path: '/specializations/',
      q: query,
      params: { is_active: true, program_id: formValues.program_id },
      mapOption: (item) => ({
        value: item.id,
        label: `${item.name} (${item.code})`,
        name: item.name,
        code: item.code,
        program_id: item.program_id
      })
    });
    mergeById(
      setSpecializations,
      options.map((item) => ({ id: item.value, name: item.name, code: item.code, program_id: item.program_id }))
    );
    return options;
  }

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

  function renderBatchGroups(specializationGroups) {
    if (!Array.isArray(specializationGroups) || specializationGroups.length === 0) {
      return null;
    }

    return specializationGroups.map((specializationGroup) => (
      <div key={specializationGroup.specialization.id}>
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200/80 bg-slate-100/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/80">
          <span className="text-sm font-semibold text-slate-900 dark:text-white">
            {specializationGroup.specialization.name}
          </span>
          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-950 dark:text-slate-300">
            {specializationGroup.specialization.code ||
              (specializationGroup.specialization.id === '__unassigned__' ? 'No specialization' : 'Specialization')}
          </span>
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 dark:bg-brand-950/40 dark:text-brand-200">
            {specializationGroup.batches.length} batch{specializationGroup.batches.length === 1 ? '' : 'es'}
          </span>
        </div>

        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {specializationGroup.batches.map((batch) => {
            const specialization = specializationMap[batch.specialization_id];
            const universityLabel = batch.university_code || batch.university_name || '-';
            return (
              <div
                key={batch.id}
                className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(0,1.2fr)_170px_180px_140px_130px_100px_110px] md:items-center"
              >
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">{batch.name}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Start {batch.start_year || '-'} | End {batch.end_year || '-'}
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
                  <button
                    type="button"
                    className="btn-secondary !p-2"
                    onClick={() => openEditModal(batch)}
                    title="Edit batch"
                  >
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
    ));
  }

  return (
    <div className="space-y-5 page-fade">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm text-sky-950 dark:border-sky-900/50 dark:bg-sky-950/30 dark:text-sky-100">
        <div className="space-y-1">
          <p className="font-semibold">Batch spans follow join year to pass-out year.</p>
          <p>
            For the Indian academic cycle, an August 2022 intake finishing in May 2026 remains a 4-year batch labeled
            <span className="font-semibold"> 2022-2026</span>. Auto-generated codes use the program prefix, while specialization-specific batches can add an extra code layer when needed, for example
            <span className="font-semibold"> B.Sc.-B22-26</span> or <span className="font-semibold"> B.Sc.-AI-B22-26</span>.
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
              loadOptions={loadProgramOptions}
              selectedLabel={programMap[programFilter] ? `${programMap[programFilter].name} (${programMap[programFilter].code})` : ''}
              allowEmpty
              emptyLabel="All Programs"
              placeholder="Filter by program"
              onValueChange={(value) => {
                setProgramFilter(value);
                setSkip(0);
              }}
            />
          </div>
          <div className="min-w-[240px] flex-1">
            <FormInput
              label="Search"
              value={searchQuery}
              placeholder="Search by batch, code, specialization, university"
              onChange={(event) => {
                setSearchQuery(event.target.value);
                setSkip(0);
              }}
            />
          </div>
          <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-3 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => {
                setShowInactive(event.target.checked);
                setSkip(0);
              }}
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
            const totalBatches = group.specializationGroups.reduce(
              (count, specializationGroup) => count + specializationGroup.batches.length,
              0
            );

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
                        {totalBatches} batch{totalBatches === 1 ? '' : 'es'}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      Program prefix: {programPrefix || '-'} | {group.program.duration_years || 4} year program | {(PROGRAM_DURATION_TO_SEMESTERS[Number(group.program.duration_years || 4)] || PROGRAM_DURATION_TO_SEMESTERS[4])} semesters
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
                      {renderBatchGroups(group.specializationGroups)}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button type="button" className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>
            Prev
          </button>
          <span className="text-xs text-slate-500">skip: {skip}</span>
          <button type="button" className="btn-secondary" disabled={batches.length < limit} onClick={() => setSkip(skip + limit)}>
            Next
          </button>
          <select className="input w-24" value={limit} onChange={(event) => { setLimit(Number(event.target.value)); setSkip(0); }}>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </Card>

      <Modal open={modalOpen} title={editingBatch ? 'Edit Batch' : 'Create Batch'} onClose={closeModal}>
        <form className="space-y-4" onSubmit={submitForm}>
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
            loadOptions={loadSpecializationOptions}
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
    </div>
  );
}

