export function buildBatchCodeSuffix(startYear, endYear) {
  if (!startYear || !endYear) return '';
  return `B${String(startYear).slice(-2)}-${String(endYear).slice(-2)}`;
}

export function buildProgramBatchPrefix(program) {
  if (!program) return '';
  const rawName = String(program.name || program.program_name || '')
    .split(/\s*(?:\(|-)\s*/, 1)[0]
    .trim();
  if (rawName) return rawName;
  return String(program.code || program.program_code || '').trim().toUpperCase();
}

export function buildSpecializationBatchPrefix(program, specialization) {
  const programPrefix = buildProgramBatchPrefix(program);
  const specializationCode = String(specialization?.code || specialization?.specialization_code || '')
    .trim()
    .toUpperCase();
  return [programPrefix, specializationCode].filter(Boolean).join('-');
}

export function buildSuggestedBatchIdentity(program, specialization, startYear, endYear) {
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
