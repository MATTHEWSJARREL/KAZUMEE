/**
 * Extract streamer_id from authenticated request.
 * Calls backend to verify token and get user's streamer_id.
 * SECURITY: Never trust client-supplied streamer_id.
 */
export async function getStreamerIdFromRequest(request) {
  try {
    // Get auth token from header
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      throw new Error('Missing or invalid Authorization header');
    }

    const token = authHeader.slice(7); // Remove 'Bearer ' prefix
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://kazumee-production.up.railway.app';

    // Verify token with backend and get streamer_id
    const response = await fetch(`${backendUrl}/api/users/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error(`Backend auth failed: ${response.status}`);
    }

    const data = await response.json();
    const streamerId = data.streamer_id;

    if (!streamerId) {
      throw new Error('No streamer_id in authenticated user');
    }

    return streamerId;
  } catch (error) {
    console.error('Auth error:', error);
    throw new Error('Unauthorized');
  }
}
