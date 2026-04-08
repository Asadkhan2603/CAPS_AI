import { describe, expect, it } from 'vitest';
import {
  recordRecentShortcut,
  resolveShortcutItems,
  sanitizeShortcutPaths,
  toggleFavoriteShortcut
} from './navigationShortcuts';

describe('navigationShortcuts', () => {
  const validPaths = ['/workspace/overview/dashboard', '/workspace/communication/notifications', '/workspace/profile/help'];
  const items = [
    { path: '/workspace/overview/dashboard', label: 'Dashboard', groupLabel: 'Overview' },
    { path: '/workspace/communication/notifications', label: 'Notifications', groupLabel: 'Communication' },
    { path: '/workspace/profile/help', label: 'Help & Support', groupLabel: 'Profile' }
  ];

  it('sanitizes shortcut paths against visibility and duplicates', () => {
    expect(
      sanitizeShortcutPaths(
        ['/workspace/profile/help', '/workspace/profile/help', '/unknown', '/workspace/overview/dashboard'],
        validPaths,
        4
      )
    ).toEqual(['/workspace/profile/help', '/workspace/overview/dashboard']);
  });

  it('records recent shortcuts with newest paths first', () => {
    expect(
      recordRecentShortcut(
        ['/workspace/profile/help', '/workspace/overview/dashboard'],
        '/workspace/communication/notifications',
        validPaths,
        3
      )
    ).toEqual([
      '/workspace/communication/notifications',
      '/workspace/profile/help',
      '/workspace/overview/dashboard'
    ]);
  });

  it('toggles favorites on and off while keeping visibility rules', () => {
    const added = toggleFavoriteShortcut(['/workspace/profile/help'], '/workspace/overview/dashboard', validPaths, 3);
    expect(added).toEqual(['/workspace/overview/dashboard', '/workspace/profile/help']);

    const removed = toggleFavoriteShortcut(added, '/workspace/profile/help', validPaths, 3);
    expect(removed).toEqual(['/workspace/overview/dashboard']);
  });

  it('resolves visible favorite and recent items without duplicates', () => {
    const { favorites, recent } = resolveShortcutItems(
      items,
      ['/workspace/profile/help'],
      ['/workspace/profile/help', '/workspace/communication/notifications']
    );

    expect(favorites.map((item) => item.label)).toEqual(['Help & Support']);
    expect(recent.map((item) => item.label)).toEqual(['Notifications']);
  });
});
