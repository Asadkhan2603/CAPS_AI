import { describe, expect, it } from 'vitest';
import {
  buildQuickSearchItems,
  findQuickSearchMatches,
  normalizeQuickSearchQuery
} from './quickSearch';

describe('quickSearch', () => {
  const items = buildQuickSearchItems(
    [
      {
        key: 'setup',
        label: 'Academic Setup',
        items: [
          { to: '/programs', label: 'Programs' },
          { to: '/batches', label: 'Batches' },
          { to: '/semesters', label: 'Semesters' }
        ]
      }
    ],
    (groupKey, itemPath) => `/workspace/${groupKey}${itemPath}`
  );

  it('normalizes whitespace and casing', () => {
    expect(normalizeQuickSearchQuery('  SeMeStErS  ')).toBe('semesters');
  });

  it('returns strong label matches first', () => {
    const matches = findQuickSearchMatches(items, 'bat');
    expect(matches[0]?.label).toBe('Batches');
    expect(matches[0]?.path).toBe('/workspace/setup/batches');
  });

  it('matches on group keywords too', () => {
    const matches = findQuickSearchMatches(items, 'academic');
    expect(matches.map((item) => item.label)).toEqual(['Batches', 'Programs', 'Semesters']);
  });
});
