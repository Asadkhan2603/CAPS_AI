function triggerDownload(filename, content) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function buildCreateStudentsTemplateCsv() {
  return [
    'full_name,email,roll_number,enrollment_number,phone',
    'Aarav Sharma,aarav.sharma@example.edu,ROLL-001,ENR-2026-001,9876543210'
  ].join('\n');
}

export function buildMapExistingTemplateCsv() {
  return [
    'student_id,enrollment_number,email,group',
    ',ENR-2026-001,,A'
  ].join('\n');
}

export function buildCreateAndMapTemplateCsv() {
  return buildCreateStudentsTemplateCsv();
}

export function downloadCreateStudentsTemplate() {
  triggerDownload('student-bulk-create-students-template.csv', buildCreateStudentsTemplateCsv());
}

export function downloadCreateAndMapTemplate() {
  downloadCreateStudentsTemplate();
}

export function downloadMapExistingTemplate() {
  triggerDownload('student-bulk-map-existing-template.csv', buildMapExistingTemplateCsv());
}
