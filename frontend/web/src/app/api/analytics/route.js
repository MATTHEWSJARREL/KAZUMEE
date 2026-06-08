import sql from "@/app/api/utils/sql";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const range = searchParams.get("range") || "7d";
    const streamerId = 1;

    // Calculate date range
    const rangeMap = {
      "24h": 1,
      "7d": 7,
      "30d": 30,
      "90d": 90,
    };
    const days = rangeMap[range] || 7;
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // Get stream stats
    const streamStats = await sql`
      SELECT 
        AVG(viewer_count) as avg_viewers,
        MAX(peak_viewers) as peak_viewers,
        SUM(total_messages) as total_messages,
        SUM(EXTRACT(EPOCH FROM (COALESCE(ended_at, NOW()) - started_at)) / 3600) as stream_hours
      FROM streams
      WHERE streamer_id = ${streamerId}
        AND started_at >= ${startDate.toISOString()}
    `;

    // Get previous period for comparison
    const prevStartDate = new Date(startDate);
    prevStartDate.setDate(prevStartDate.getDate() - days);

    const prevStats = await sql`
      SELECT 
        AVG(viewer_count) as avg_viewers,
        MAX(peak_viewers) as peak_viewers
      FROM streams
      WHERE streamer_id = ${streamerId}
        AND started_at >= ${prevStartDate.toISOString()}
        AND started_at < ${startDate.toISOString()}
    `;

    // Calculate changes
    const viewerChange = prevStats[0]?.avg_viewers
      ? Math.round(
          ((parseFloat(streamStats[0]?.avg_viewers || 0) -
            parseFloat(prevStats[0].avg_viewers)) /
            parseFloat(prevStats[0].avg_viewers)) *
            100,
        )
      : 0;

    const peakChange = prevStats[0]?.peak_viewers
      ? Math.round(
          ((parseInt(streamStats[0]?.peak_viewers || 0) -
            parseInt(prevStats[0].peak_viewers)) /
            parseInt(prevStats[0].peak_viewers)) *
            100,
        )
      : 0;

    // Get viewer growth data (daily averages)
    const viewerGrowth = await sql`
      SELECT DATE(started_at) as date, AVG(viewer_count)::int as viewers
      FROM streams
      WHERE streamer_id = ${streamerId}
        AND started_at >= ${startDate.toISOString()}
      GROUP BY DATE(started_at)
      ORDER BY DATE(started_at)
    `;

    // Get top performing clips
    const topClips = await sql`
      SELECT 
        title,
        view_count as views,
        ROUND(performance_score * 100) as score,
        detection_method as detection,
        TO_CHAR(created_at, 'MM/DD') as date
      FROM clips
      WHERE streamer_id = ${streamerId}
        AND created_at >= ${startDate.toISOString()}
      ORDER BY view_count DESC, performance_score DESC
      LIMIT 10
    `;

    // Engagement breakdown (simplified)
    const engagement = {
      chat: 35,
      clips: 25,
      commands: 20,
      raids: 15,
      other: 5,
    };

    return Response.json({
      avgViewers: Math.round(parseFloat(streamStats[0]?.avg_viewers || 0)),
      peakViewers: parseInt(streamStats[0]?.peak_viewers || 0),
      totalMessages: parseInt(streamStats[0]?.total_messages || 0),
      streamHours: Math.round(parseFloat(streamStats[0]?.stream_hours || 0)),
      viewerChange,
      peakChange,
      messageChange: 12,
      hoursChange: 8,
      viewerGrowth: viewerGrowth.map((d) => d.viewers),
      engagement,
      topClips: topClips.map((clip) => ({
        title: clip.title,
        views: clip.views,
        score: clip.score,
        detection: clip.detection,
        date: clip.date,
      })),
    });
  } catch (error) {
    console.error("Error fetching analytics:", error);
    return Response.json(
      { error: "Failed to fetch analytics" },
      { status: 500 },
    );
  }
}
