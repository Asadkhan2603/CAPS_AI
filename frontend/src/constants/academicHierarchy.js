export const ACADEMIC_HIERARCHY_MODEL =
  'University -> Faculty -> Department -> Program -> (optional) Specialization -> Batch -> Semester -> Section -> Group';

export const PROGRAM_DURATION_TO_SEMESTERS = {
  1: 2,
  2: 4,
  3: 6,
  4: 8,
  5: 10
};

export const PROGRAM_DURATION_OPTIONS = Object.entries(PROGRAM_DURATION_TO_SEMESTERS).map(([years, semesters]) => ({
  value: Number(years),
  label: `${years} year${Number(years) === 1 ? '' : 's'} (${semesters} semesters)`
}));
