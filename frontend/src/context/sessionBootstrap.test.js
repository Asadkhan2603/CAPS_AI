import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchSessionBootstrap,
  resetSessionBootstrapTransportCache
} from './sessionBootstrap';

describe('fetchSessionBootstrap', () => {
  beforeEach(() => {
    resetSessionBootstrapTransportCache();
  });

  it('uses the consolidated endpoint when available', async () => {
    const apiClient = {
      get: vi.fn().mockResolvedValueOnce({
        data: {
          user: { id: 'user-1', email: 'user@example.com' },
          unread_notice_count: 3,
          branding: { has_logo: true, updated_at: '2026-04-02T12:00:00Z', filename: 'logo.svg' },
          generated_at: '2026-04-02T12:00:00Z'
        }
      })
    };

    await expect(fetchSessionBootstrap(apiClient)).resolves.toEqual({
      user: { id: 'user-1', email: 'user@example.com' },
      unread_notice_count: 3,
      branding: { has_logo: true, updated_at: '2026-04-02T12:00:00Z', filename: 'logo.svg' },
      generated_at: '2026-04-02T12:00:00Z'
    });
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    expect(apiClient.get).toHaveBeenCalledWith('/session/bootstrap');
  });

  it('falls back to legacy endpoints when the consolidated route is missing', async () => {
    const apiClient = {
      get: vi
        .fn()
        .mockRejectedValueOnce({ response: { status: 404 } })
        .mockResolvedValueOnce({ data: { id: 'user-2', email: 'legacy@example.com' } })
        .mockResolvedValueOnce({ data: { count: 7 } })
        .mockResolvedValueOnce({ data: { has_logo: true, updated_at: '2026-04-02T12:05:00Z', filename: 'logo.png' } })
    };

    await expect(fetchSessionBootstrap(apiClient)).resolves.toMatchObject({
      user: { id: 'user-2', email: 'legacy@example.com' },
      unread_notice_count: 7,
      branding: { has_logo: true, updated_at: '2026-04-02T12:05:00Z', filename: 'logo.png' }
    });

    expect(apiClient.get.mock.calls).toEqual([
      ['/session/bootstrap'],
      ['/auth/me'],
      ['/notices/unread-count'],
      ['/branding/logo/meta']
    ]);
  });

  it('caches the legacy transport after a missing consolidated route', async () => {
    const apiClient = {
      get: vi
        .fn()
        .mockRejectedValueOnce({ response: { status: 404 } })
        .mockResolvedValue({ data: { id: 'user-3', email: 'cached@example.com' } })
    };

    apiClient.get
      .mockResolvedValueOnce({ data: { id: 'user-3', email: 'cached@example.com' } })
      .mockResolvedValueOnce({ data: { count: 0 } })
      .mockResolvedValueOnce({ data: { has_logo: false } });

    await fetchSessionBootstrap(apiClient);

    apiClient.get.mockClear();
    apiClient.get
      .mockResolvedValueOnce({ data: { id: 'user-3', email: 'cached@example.com' } })
      .mockResolvedValueOnce({ data: { count: 1 } })
      .mockResolvedValueOnce({ data: { has_logo: false } });

    await fetchSessionBootstrap(apiClient);

    expect(apiClient.get.mock.calls).toEqual([
      ['/auth/me'],
      ['/notices/unread-count'],
      ['/branding/logo/meta']
    ]);
  });
});
