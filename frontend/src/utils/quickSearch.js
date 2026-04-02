export function normalizeQuickSearchQuery(value) {
  return String(value || '').trim().toLowerCase();
}

export function buildQuickSearchItems(navigationGroups, getPath) {
  return (navigationGroups || []).flatMap((group) =>
    (group.items || []).map((item) => ({
      id: `${group.key}:${item.to}`,
      label: item.label,
      groupLabel: group.label,
      keywords: `${group.label} ${item.label} ${item.to}`,
      path: getPath(group.key, item.to)
    }))
  );
}

export function findQuickSearchMatches(items, query, limit = 6) {
  const normalizedQuery = normalizeQuickSearchQuery(query);
  if (!normalizedQuery) return [];

  return (items || [])
    .map((item) => {
      const searchableText = `${item.label} ${item.groupLabel} ${item.keywords || ''}`.toLowerCase();
      const startsWithLabel = item.label.toLowerCase().startsWith(normalizedQuery);
      const includesLabel = item.label.toLowerCase().includes(normalizedQuery);
      const includesAny = searchableText.includes(normalizedQuery);
      if (!includesAny) return null;

      let score = 0;
      if (startsWithLabel) score += 4;
      if (includesLabel) score += 2;
      if (item.groupLabel?.toLowerCase().includes(normalizedQuery)) score += 1;

      return { ...item, score };
    })
    .filter(Boolean)
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return left.label.localeCompare(right.label);
    })
    .slice(0, limit);
}
