import { describe, expect, it } from 'vitest';
import {
  buildBatchCodeSuffix,
  buildProgramBatchPrefix,
  buildSpecializationBatchPrefix,
  buildSuggestedBatchIdentity
} from './academicBatchIdentity';

describe('academicBatchIdentity', () => {
  it('builds the backend-aligned year suffix', () => {
    expect(buildBatchCodeSuffix(2022, 2026)).toBe('B22-26');
  });

  it('prefers the readable program display prefix', () => {
    expect(buildProgramBatchPrefix({ name: 'B.Sc. (Hons)', code: 'SCI-P01' })).toBe('B.Sc.');
    expect(buildProgramBatchPrefix({ name: 'B.Tech - CSE', code: 'ENG-P01' })).toBe('B.Tech');
  });

  it('includes specialization codes only when present', () => {
    expect(buildSpecializationBatchPrefix({ name: 'B.Sc.' }, null)).toBe('B.Sc.');
    expect(buildSpecializationBatchPrefix({ name: 'B.Sc.' }, { code: 'AI' })).toBe('B.Sc.-AI');
  });

  it('builds deterministic suggested identities for manual creation', () => {
    expect(
      buildSuggestedBatchIdentity({ name: 'B.Sc.' }, { code: 'AI' }, 2022, 2026)
    ).toEqual({
      name: 'Batch 2022-2026',
      code: 'B.Sc.-AI-B22-26'
    });

    expect(buildSuggestedBatchIdentity({ name: 'B.Sc.' }, null, 2022, 2026)).toEqual({
      name: 'Batch 2022-2026',
      code: 'B.Sc.-B22-26'
    });
  });
});
