import { beforeAll, beforeEach, describe, expect, it } from 'vitest';
import {
  REFRESH_TOKEN_KEY,
  TOKEN_KEY,
  USER_KEY,
  clearAuthStorage,
  getAccessToken,
  readAuthStorage,
  setAccessToken,
  writeAuthStorage
} from './apiClient';

function createStorage() {
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
}

beforeAll(() => {
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: createStorage()
  });
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: createStorage()
  });
});

beforeEach(() => {
  globalThis.sessionStorage.clear();
  globalThis.localStorage.clear();
  clearAuthStorage();
});

describe('apiClient auth storage', () => {
  it('keeps access tokens in memory only', () => {
    writeAuthStorage(TOKEN_KEY, 'legacy-token');

    setAccessToken('access-token');

    expect(getAccessToken()).toBe('access-token');
    expect(readAuthStorage(TOKEN_KEY)).toBe('');
  });

  it('clears stored refresh and user state together with the in-memory token', () => {
    setAccessToken('access-token');
    writeAuthStorage(REFRESH_TOKEN_KEY, 'refresh-token');
    writeAuthStorage(USER_KEY, '{"id":"user-1"}');

    clearAuthStorage();

    expect(getAccessToken()).toBe('');
    expect(readAuthStorage(REFRESH_TOKEN_KEY)).toBe('');
    expect(readAuthStorage(USER_KEY)).toBe('');
  });
});
