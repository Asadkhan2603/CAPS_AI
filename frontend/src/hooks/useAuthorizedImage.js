import { useEffect, useState } from 'react';
import { apiClient } from '../services/apiClient';

function normalizeRequestPath(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) {
    try {
      const url = new URL(path);
      return `${url.pathname}${url.search || ''}`;
    } catch {
      return path;
    }
  }
  const basePath = String(apiClient.defaults.baseURL || '/api/v1').replace(/\/+$/, '');
  if (path === basePath) return '/';
  if (path.startsWith(`${basePath}/`)) {
    return path.slice(basePath.length);
  }
  return path;
}

export function useAuthorizedImage(path, cacheBuster) {
  const [src, setSrc] = useState('');

  useEffect(() => {
    let mounted = true;
    let objectUrl = '';

    async function loadImage() {
      const requestPath = normalizeRequestPath(path);
      if (!requestPath) {
        setSrc('');
        return;
      }
      try {
        const response = await apiClient.get(requestPath, {
          responseType: 'blob',
          params: cacheBuster ? { v: cacheBuster } : undefined
        });
        if (!mounted || !response?.data || response.data.size === 0) {
          return;
        }
        objectUrl = URL.createObjectURL(response.data);
        setSrc(objectUrl);
      } catch {
        if (mounted) {
          setSrc('');
        }
      }
    }

    loadImage();

    return () => {
      mounted = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [path, cacheBuster]);

  return src;
}
