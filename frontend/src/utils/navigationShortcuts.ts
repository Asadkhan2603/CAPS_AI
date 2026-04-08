export type NavigationShortcutItem = {
  path: string;
  label: string;
  groupLabel?: string;
};

function uniquePaths(paths: string[]) {
  return Array.from(new Set((paths || []).filter(Boolean)));
}

export function readStoredShortcutPaths(storageKey: string) {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((value) => typeof value === 'string') : [];
  } catch {
    return [];
  }
}

export function writeStoredShortcutPaths(storageKey: string, paths: string[]) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(storageKey, JSON.stringify(uniquePaths(paths)));
}

export function sanitizeShortcutPaths(paths: string[], validPaths: string[], limit = 6) {
  const allowed = new Set(validPaths || []);
  return uniquePaths(paths).filter((path) => allowed.has(path)).slice(0, limit);
}

export function recordRecentShortcut(paths: string[], path: string, validPaths: string[], limit = 5) {
  if (!path || !validPaths.includes(path)) {
    return sanitizeShortcutPaths(paths, validPaths, limit);
  }

  return [path, ...uniquePaths(paths).filter((entry) => entry !== path)]
    .filter((entry) => validPaths.includes(entry))
    .slice(0, limit);
}

export function toggleFavoriteShortcut(paths: string[], path: string, validPaths: string[], limit = 6) {
  if (!path || !validPaths.includes(path)) {
    return sanitizeShortcutPaths(paths, validPaths, limit);
  }

  if (paths.includes(path)) {
    return paths.filter((entry) => entry !== path);
  }

  return [path, ...uniquePaths(paths)].filter((entry) => validPaths.includes(entry)).slice(0, limit);
}

export function resolveShortcutItems(
  items: NavigationShortcutItem[],
  favoritePaths: string[],
  recentPaths: string[]
) {
  const lookup = new Map((items || []).map((item) => [item.path, item]));
  const favorites = sanitizeShortcutPaths(favoritePaths, items.map((item) => item.path)).map((path) => lookup.get(path)).filter(Boolean) as NavigationShortcutItem[];
  const favoritePathSet = new Set(favorites.map((item) => item.path));
  const recent = sanitizeShortcutPaths(recentPaths, items.map((item) => item.path))
    .filter((path) => !favoritePathSet.has(path))
    .map((path) => lookup.get(path))
    .filter(Boolean) as NavigationShortcutItem[];

  return { favorites, recent };
}
