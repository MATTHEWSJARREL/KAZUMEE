import { useState, useCallback } from 'react';
import { toast } from 'sonner';

interface UseApiOptions {
  retries?: number;
  timeout?: number;
  showError?: boolean;
  showSuccess?: boolean;
}

interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

/**
 * Hook for API calls with error handling, retry logic, and loading states
 */
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchWithRetry = useCallback(
    async (
      url: string,
      options: RequestInit = {},
      apiOptions: UseApiOptions = {}
    ) => {
      const {
        retries = 2,
        timeout = 30000,
        showError = true,
        showSuccess = false
      } = apiOptions;

      setLoading(true);
      setError(null);

      let lastError: ApiError | null = null;

      for (let attempt = 0; attempt <= retries; attempt++) {
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), timeout);

          const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
              ...options.headers
            }
          });

          clearTimeout(timeoutId);

          // Handle auth errors specially
          if (response.status === 401) {
            localStorage.clear();
            window.location.href = '/auth';
            throw new Error('Session expired. Please log in again.');
          }

          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            lastError = {
              status: response.status,
              message: data.detail || `HTTP ${response.status}`,
              detail: data.detail
            };

            // Don't retry on client errors (except 429)
            if (response.status >= 400 && response.status < 500 && response.status !== 429) {
              throw lastError;
            }

            // Retry on server errors or rate limiting
            if (attempt < retries) {
              await new Promise(res => setTimeout(res, Math.pow(2, attempt) * 1000));
              continue;
            }
            throw lastError;
          }

          setLoading(false);
          setError(null);

          if (showSuccess) {
            toast.success('Success!');
          }

          return response;
        } catch (err: any) {
          lastError = {
            status: err.status || 0,
            message: err.message || 'Unknown error',
            detail: err.detail
          };

          if (err.name === 'AbortError') {
            lastError.message = 'Request timeout';
          }

          if (attempt === retries) {
            break;
          }

          // Wait before retrying
          await new Promise(res => setTimeout(res, Math.pow(2, attempt) * 1000));
        }
      }

      // All retries exhausted
      setLoading(false);
      setError(lastError);

      if (showError && lastError) {
        toast.error(lastError.message);
      }

      throw lastError;
    },
    []
  );

  return {
    loading,
    error,
    fetchWithRetry,
    clearError: () => setError(null)
  };
}

/**
 * Helper for common API operations
 */
export const apiClient = {
  get: async (url: string, token: string | null) => {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token || localStorage.getItem('authToken')}`
      }
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  },

  post: async (url: string, data: any, token: string | null = null) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token || localStorage.getItem('authToken')}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }
    return response.json();
  },

  put: async (url: string, data: any, token: string | null = null) => {
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token || localStorage.getItem('authToken')}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }
    return response.json();
  },

  delete: async (url: string, token: string | null = null) => {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token || localStorage.getItem('authToken')}`
      }
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }
    return response.json().catch(() => ({}));
  }
};
