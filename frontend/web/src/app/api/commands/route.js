import sql from "@/app/api/utils/sql";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status") || "all";
    const tier = searchParams.get("tier") || "all";
    const streamerId = 1;

    // Get current stream
    const currentStream = await sql`
      SELECT id FROM streams
      WHERE streamer_id = ${streamerId} AND status = 'live'
      ORDER BY started_at DESC LIMIT 1
    `;

    if (currentStream.length === 0) {
      return Response.json({ commands: [] });
    }

    let query = `
      SELECT 
        cq.*,
        v.username as viewer_username,
        v.tier as viewer_tier
      FROM command_queue cq
      JOIN viewers v ON cq.viewer_id = v.id
      WHERE cq.stream_id = $1
    `;
    const params = [currentStream[0].id];
    let paramCount = 2;

    if (status !== "all") {
      query += ` AND cq.status = $${paramCount}`;
      params.push(status);
      paramCount++;
    }

    if (tier !== "all") {
      query += ` AND v.tier = $${paramCount}`;
      params.push(tier);
      paramCount++;
    }

    query += " ORDER BY cq.priority DESC, cq.created_at ASC";

    const commands = await sql(query, params);

    return Response.json({ commands });
  } catch (error) {
    console.error("Error fetching commands:", error);
    return Response.json(
      { error: "Failed to fetch commands" },
      { status: 500 },
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const { streamId, viewerId, commandType, commandText, priority } = body;

    const result = await sql`
      INSERT INTO command_queue 
        (stream_id, viewer_id, command_type, command_text, priority, status)
      VALUES 
        (${streamId}, ${viewerId}, ${commandType}, ${commandText}, ${priority || 0}, 'pending')
      RETURNING *
    `;

    return Response.json({ success: true, command: result[0] });
  } catch (error) {
    console.error("Error creating command:", error);
    return Response.json(
      { error: "Failed to create command" },
      { status: 500 },
    );
  }
}
