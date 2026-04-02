import { beforeEach, describe, expect, it, vi } from 'vitest';

const getMock = vi.fn();

vi.mock('./apiClient', () => ({
  apiClient: {
    get: (...args) => getMock(...args)
  }
}));

const storageFactory = () => {
  const store = new Map();
  return {
    clear() {
      store.clear();
    },
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    removeItem(key) {
      store.delete(key);
    },
    setItem(key, value) {
      store.set(key, String(value));
    }
  };
};

beforeEach(() => {
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: storageFactory()
  });
  getMock.mockReset();
});

const module = await import('./paginatedLookups');

describe('paginatedLookups cache', () => {
  beforeEach(() => {
    module.clearLookupCache();
  });

  it('reuses cached lookup options across repeated calls', async () => {
    getMock.mockResolvedValue({
      data: [{ id: 'prog-1', name: 'Computer Science', code: 'CSE' }]
    });

    const first = await module.searchLookupOptions({ path: '/programs/' });
    const second = await module.searchLookupOptions({ path: '/programs/' });

    expect(first).toEqual(second);
    expect(getMock).toHaveBeenCalledTimes(1);
  });

  it('invalidates dependent academic lookups after parent mutations', async () => {
    getMock.mockResolvedValue({
      data: [{ id: 'batch-1', name: 'Batch 2024', code: 'B24' }]
    });

    await module.searchLookupOptions({ path: '/batches/', params: { program_id: 'prog-1' } });
    expect(getMock).toHaveBeenCalledTimes(1);

    module.invalidateLookupCacheForPath('/programs/');
    await module.searchLookupOptions({ path: '/batches/', params: { program_id: 'prog-1' } });

    expect(getMock).toHaveBeenCalledTimes(2);
  });
});
