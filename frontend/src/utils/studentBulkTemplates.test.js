import { describe, expect, it } from 'vitest';

import { buildCreateAndMapTemplateCsv, buildMapExistingTemplateCsv } from './studentBulkTemplates';

describe('student bulk templates', () => {
  it('builds the create-and-map CSV template with the expected headers and sample row', () => {
    expect(buildCreateAndMapTemplateCsv()).toBe(
      'full_name,email,roll_number,enrollment_number,phone\n' +
        'Aarav Sharma,aarav.sharma@example.edu,ROLL-001,ENR-2026-001,9876543210'
    );
  });

  it('builds the map-existing CSV template with the expected headers and sample row', () => {
    expect(buildMapExistingTemplateCsv()).toBe(
      'student_id,enrollment_number,email,group\n' +
        ',ENR-2026-001,,A'
    );
  });
});
