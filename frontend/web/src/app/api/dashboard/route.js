import sql from "@/app/api/utils/sql";

export async function GET(request) {
  try {
    const streamerId = 1; // Default streamer for now

    // Get current stream
    const currentStreamResult = await sql`
      SELECT * FROM streams 
      WHERE streamer_id = ${streamerId} AND status = 'live'
      ORDER BY started_at DESC LIMIT 1
    `;
    const currentStream = currentStreamResult[0];

    // Get stream health if stream is live
    let healthData = null;
    if (currentStream) {
      const healthResult = await sql`
        SELECT * FROM stream_health_metrics 
        WHERE stream_id = ${currentStream.id}
        ORDER BY timestamp DESC LIMIT 1
      `;
      healthData = healthResult[0];
    }

    // Get clips count for today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const clipsResult = await sql`
      SELECT 
        COUNT(*) as total_clips,
        COUNT(*) FILTER (WHERE auto_detected = true) as auto_clips,
        COUNT(*) FILTER (WHERE auto_detected = false) as manual_clips
      FROM clips
      WHERE streamer_id = ${streamerId}
        AND created_at >= ${today.toISOString()}
    `;

    // Get moderation events count for today
    const modResult = await sql`
      SELECT 
        COUNT(*) as total_events,
        COUNT(*) FILTER (WHERE auto_moderated = true) as auto_moderated
      FROM moderation_events
      WHERE streamer_id = ${streamerId}
        AND created_at >= ${today.toISOString()}
    `;

    // Get recent activity (clips, moderation, commands)
    const recentClips = await sql`
      SELECT 'clip' as type, title as description, 
             'completed' as status, created_at as time
      FROM clips
      WHERE streamer_id = ${streamerId}
      ORDER BY created_at DESC LIMIT 3
    `;

    const recentMods = await sql`
      SELECT 'moderation' as type, 
             CONCAT('Moderated user: ', username) as description,
             CASE WHEN reviewed THEN 'completed' ELSE 'pending' END as status,
             created_at as time
      FROM moderation_events
      WHERE streamer_id = ${streamerId}
      ORDER BY created_at DESC LIMIT 3
    `;

    const recentCommands = await sql`
      SELECT 'command' as type, command_text as description,
             status, created_at as time
      FROM command_queue
      WHERE stream_id = ${currentStream?.id || 0}
      ORDER BY created_at DESC LIMIT 3
    `;

    const recentActivity = [...recentClips, ...recentMods, ...recentCommands]
      .sort((a, b) => new Date(b.time) - new Date(a.time))
      .slice(0, 10)
      .map((activity) => ({
        ...activity,
        time: new Date(activity.time).toLocaleTimeString(),
      }));

    // Get ML confidence from latest learning data
    const mlDataResult = await sql`
      SELECT AVG(confidence_score) as avg_confidence
      FROM ml_learning_data
      WHERE streamer_id = ${streamerId}
        AND created_at >= NOW() - INTERVAL '7 days'
    `;

    const dashboardData = {
      currentViewers: currentStream?.viewer_count || 0,
      viewerChange: currentStream ? "+12.5%" : "+0%",
      healthStatus: healthData?.health_status || "Healthy",
      healthScore: healthData
        ? Math.round(healthData.prediction_score * 100)
        : 95,
      autoClips: clipsResult[0]?.auto_clips || 0,
      manualClips: clipsResult[0]?.manual_clips || 0,
      modEvents: modResult[0]?.total_events || 0,
      autoModerated: modResult[0]?.auto_moderated
        ? Math.round(
            (modResult[0].auto_moderated / modResult[0].total_events) * 100,
          )
        : 0,
      mlConfidence: mlDataResult[0]?.avg_confidence
        ? Math.round(mlDataResult[0].avg_confidence * 100)
        : 85,
      userName: "KazumiPro",
      recentActivity,
      streamMetrics: {
        avgViewers: currentStream?.viewer_count || 0,
      },
    };

    return Response.json(dashboardData);
  } catch (error) {
    console.error("Error fetching dashboard data:", error);
    return Response.json(
      { error: "Failed to fetch dashboard data" },
      { status: 500 },
    );
  }
}
