import sql from "@/app/api/utils/sql";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const filter = searchParams.get("filter") || "all";
    const streamerId = 1; // Default streamer for now

    let query = "SELECT * FROM clips WHERE streamer_id = $1";
    const params = [streamerId];

    if (filter === "auto") {
      query += " AND auto_detected = true";
    } else if (filter === "manual") {
      query += " AND auto_detected = false";
    }

    query += " ORDER BY created_at DESC";

    const clips = await sql(query, params);

    return Response.json({ clips });
  } catch (error) {
    console.error("Error fetching clips:", error);
    return Response.json({ error: "Failed to fetch clips" }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      streamId,
      streamerId,
      title,
      description,
      timestampStart,
      timestampEnd,
      detectionMethod,
      autoDetected,
      tags,
    } = body;

    const result = await sql`
      INSERT INTO clips 
        (stream_id, streamer_id, title, description, timestamp_start, timestamp_end,
         detection_method, auto_detected, tags)
      VALUES 
        (${streamId}, ${streamerId}, ${title}, ${description}, ${timestampStart}, 
         ${timestampEnd}, ${detectionMethod || "manual"}, ${autoDetected || false}, 
         ${tags || []})
      RETURNING *
    `;

    return Response.json({ success: true, clip: result[0] });
  } catch (error) {
    console.error("Error creating clip:", error);
    return Response.json({ error: "Failed to create clip" }, { status: 500 });
  }
}
