import { apiFetch } from './apiClient';
import { toast } from 'sonner';

/**
 * Wrapper around apiFetch that handles 403 "Not a streamer" errors
 * Shows a friendly "Coming soon for viewers" message
 */
export async function apiFetchWithErrorHandling(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const response = await apiFetch(path, options);

  // Check for 403 Forbidden errors (viewer trying to access streamer features)
  if (response.status === 403) {
    const responseText = await response.text();

    // Check if this is a "Not a streamer" error
    if (responseText.includes('Not a streamer') || responseText.includes('viewer')) {
      toast.info('👀 Coming soon for viewers!\nStreamer features launching soon.', {
        duration: 5000,
      });
    }

    // Return a new response to avoid consuming the body twice
    return new Response(responseText, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  }

  return response;
}
