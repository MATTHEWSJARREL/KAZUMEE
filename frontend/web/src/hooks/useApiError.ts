import { useEffect } from 'react';
import { toast } from 'sonner';

/**
 * Hook that globally handles API 403 errors from clip endpoints
 * Shows "Coming soon for viewers" message when viewer tries to access streamer features
 * Should be called once in the root app layout
 */
export function useApiErrorHandler() {
  useEffect(() => {
    const originalFetch = window.fetch;
    let shown403Toast = false;

    window.fetch = function (...args: any) {
      const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';

      return originalFetch.apply(this, args).then(async (response: Response) => {
        // Check for 403 Forbidden on clip/streamer endpoints
        if (response.status === 403 && url.includes('/api/clips')) {
          try {
            const clonedResponse = response.clone();
            const text = await clonedResponse.text();

            // Check if it's a "Not a streamer" error
            if (text.includes('Not a streamer') || text.includes('streamer role')) {
              // Only show toast once per session to avoid spam
              if (!shown403Toast) {
                shown403Toast = true;
                toast.info('👀 Coming soon for viewers!\nStreamer features launching soon.', {
                  duration: 5000,
                });
                // Reset after timeout
                setTimeout(() => { shown403Toast = false; }, 10000);
              }
            }
          } catch (e) {
            // If body reading fails, still show generic message
            if (!shown403Toast) {
              shown403Toast = true;
              toast.info('👀 Coming soon for viewers!\nStreamer features launching soon.', {
                duration: 5000,
              });
              setTimeout(() => { shown403Toast = false; }, 10000);
            }
          }
        }
        return response;
      });
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);
}
