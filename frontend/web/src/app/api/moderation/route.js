import sql from "@/app/api/utils/sql";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const severity = searchParams.get("severity") || "all";
    const streamerId = 1; // Default streamer for now

    let query = "SELECT * FROM moderation_events WHERE streamer_id = $1";
    const params = [streamerId];

    if (severity !== "all") {
      query += " AND severity = $2";
      params.push(severity);
    }

    query += " ORDER BY created_at DESC";

    const events = await sql(query, params);

    return Response.json({ events });
  } catch (error) {
    console.error("Error fetching moderation events:", error);
    return Response.json(
      { error: "Failed to fetch moderation events" },
      { status: 500 },
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      streamId,
      streamerId,
      username,
      userId,
      eventType,
      severity,
      messageContent,
      actionTaken,
      autoModerated,
    } = body;

    const result = await sql`
      INSERT INTO moderation_events 
        (stream_id, streamer_id, username, user_id, event_type, severity,
         message_content, action_taken, auto_moderated)
      VALUES 
        (${streamId}, ${streamerId}, ${username}, ${userId}, ${eventType},
         ${severity}, ${messageContent}, ${actionTaken}, ${autoModerated || false})
      RETURNING *
    `;

    return Response.json({ success: true, event: result[0] });
  } catch (error) {
    console.error("Error creating moderation event:", error);
    return Response.json(
      { error: "Failed to create moderation event" },
      { status: 500 },
    );
  }
}
