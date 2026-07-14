import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRealtime } from '@/lib/realtime';

const ClipSearchContext = createContext({ results: [], setResults: () => {} });

export function ClipSearchProvider({ children }) {
  const [results, setResults] = useState([]);
  const { subscribeToType } = useRealtime();

  useEffect(() => {
    const handler = (ev) => {
      try {
        const data = ev?.data;
        if (!data) return;
        if (data.type === 'search_results') {
          const r = data.data?.results || [];
          setResults(r);
          console.log('Search results received (window):', r);
        }
      } catch (err) {
        // swallow
      }
    };

    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeToType('search_results', (message) => {
      try {
        const r = message?.data?.results || [];
        setResults(r);
        console.log('Search results received (realtime):', r);
      } catch (error) {
        // ignore
      }
    });

    return () => unsubscribe();
  }, [subscribeToType]);

  return (
    <ClipSearchContext.Provider value={{ results, setResults }}>{children}</ClipSearchContext.Provider>
  );
}

export function useClipSearch() {
  return useContext(ClipSearchContext);
}

export default ClipSearchContext;
