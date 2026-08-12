import sql from "@/app/api/utils/sql";
import { getStreamerIdFromRequest } from "@/app/api/utils/getStreamerIdFromRequest";

export async function GET(request) {
  try {
    const streamerId = await getStreamerIdFromRequest(request);

    // Get viewer info
    const viewer = await sql`
      SELECT * FROM viewers WHERE id = ${viewerId}
    `;

    // Get current live stream
    const currentStream = await sql`
      SELECT * FROM streams
      WHERE streamer_id = ${streamerId} AND status = 'live'
      ORDER BY started_at DESC LIMIT 1
    `;

    // Get viewer's saved clips (simplified - would join with a saved_clips table in production)
    const yourClips = await sql`
      SELECT * FROM clips
      WHERE streamer_id = ${streamerId}
      ORDER BY created_at DESC
      LIMIT 10
    `;

    // Get lore suggestions based on community culture
    const loreSuggestions = await sql`
      SELECT key_phrase, context
      FROM community_culture
      WHERE streamer_id = ${streamerId}
        AND culture_type IN ('lore', 'inside_joke')
      ORDER BY frequency DESC
      LIMIT 3
    `;

    return Response.json({
      viewer: viewer[0],
      currentStream: currentStream[0] || null,
      yourClips,
      loreSuggestions: loreSuggestions.map(
        (l) => `${l.key_phrase}: ${l.context}`,
      ),
    });
  } catch (error) {
    console.error("Error fetching viewer dashboard:", error);
    return Response.json(
      { error: "Failed to fetch viewer dashboard" },
      { status: 500 },
    );
  }
}
