'use client';

import { useCallback, useSyncExternalStore } from 'react';

/**
 * Media query as an external store, so the value is read during render rather
 * than pushed in from an effect (which causes a cascading render on mount).
 */
export function useMediaQuery(query: string, serverValue = false): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mql = window.matchMedia(query);
      mql.addEventListener('change', onChange);
      return () => mql.removeEventListener('change', onChange);
    },
    [query]
  );

  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => serverValue
  );
}
