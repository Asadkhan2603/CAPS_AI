import { lazy } from 'react';

const RELOAD_ONCE_KEY = 'caps_ai_lazy_reload_once';

function isRecoverableChunkError(error) {
  const message = String(error?.message || error || '').toLowerCase();
  return (
    message.includes('failed to fetch dynamically imported module') ||
    message.includes('error loading dynamically imported module') ||
    message.includes('importing a module script failed') ||
    message.includes('chunk load error') ||
    message.includes('load failed')
  );
}

function tryReloadOnce() {
  try {
    const alreadyReloaded = sessionStorage.getItem(RELOAD_ONCE_KEY) === '1';
    if (!alreadyReloaded) {
      sessionStorage.setItem(RELOAD_ONCE_KEY, '1');
      window.location.reload();
      return true;
    }
  } catch {
    window.location.reload();
    return true;
  }
  return false;
}

export function lazyWithRetry(importer) {
  return lazy(async () => {
    try {
      return await importer();
    } catch (error) {
      if (isRecoverableChunkError(error) && tryReloadOnce()) {
        return new Promise(() => {});
      }
      throw error;
    }
  });
}

