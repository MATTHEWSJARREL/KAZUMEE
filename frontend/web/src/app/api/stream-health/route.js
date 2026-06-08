import sql from "@/app/api/utils/sql";

export async function GET(request) {
  try {
    const streamerId = 1; // Default streamer for now

    // Get current live stream
    const currentStreamResult = await sql`
      SELECT * FROM streams 
      WHERE streamer_id = ${streamerId} AND status = 'live'
      ORDER BY started_at DESC LIMIT 1
    `;
    const currentStream = currentStreamResult[0];

    if (!currentStream) {
      return Response.json({
        healthStatus: "offline",
        cpuUsage: 0,
        gpuUsage: 0,
        memoryUsage: 0,
        networkLatency: 0,
        bitrate: 0,
        droppedFrames: 0,
        predictionScore: 0,
        predictions: [],
      });
    }

    // Get latest health metrics
    const healthResult = await sql`
      SELECT * FROM stream_health_metrics 
      WHERE stream_id = ${currentStream.id}
      ORDER BY timestamp DESC LIMIT 1
    `;
    const healthData = healthResult[0];

    if (!healthData) {
      return Response.json({
        healthStatus: "unknown",
        cpuUsage: 0,
        gpuUsage: 0,
        memoryUsage: 0,
        networkLatency: 0,
        bitrate: 0,
        droppedFrames: 0,
        predictionScore: 0,
        predictions: [],
      });
    }

    // Generate AI predictions based on current metrics
    const predictions = [];

    if (parseFloat(healthData.cpu_usage) > 80) {
      predictions.push({
        severity: "high",
        message:
          "CPU usage is critically high. Consider reducing stream quality or closing background apps.",
        confidence: 92,
      });
    }

    if (parseFloat(healthData.gpu_usage) > 90) {
      predictions.push({
        severity: "high",
        message:
          "GPU usage approaching maximum. Stream quality degradation likely.",
        confidence: 88,
      });
    }

    if (healthData.dropped_frames > 50) {
      predictions.push({
        severity: "medium",
        message:
          "Dropped frames detected. Check network stability and encoding settings.",
        confidence: 85,
      });
    }

    if (healthData.network_latency > 50) {
      predictions.push({
        severity: "medium",
        message:
          "Network latency is elevated. Stream buffering may occur for viewers.",
        confidence: 78,
      });
    }

    if (predictions.length === 0 && healthData.prediction_score > 0.9) {
      predictions.push({
        severity: "low",
        message: "Stream health is optimal. All systems operating normally.",
        confidence: 95,
      });
    }

    const responseData = {
      healthStatus: healthData.health_status,
      cpuUsage: parseFloat(healthData.cpu_usage) || 0,
      gpuUsage: parseFloat(healthData.gpu_usage) || 0,
      memoryUsage: parseFloat(healthData.memory_usage) || 0,
      networkLatency: healthData.network_latency || 0,
      bitrate: healthData.bitrate || 0,
      droppedFrames: healthData.dropped_frames || 0,
      predictionScore: Math.round((healthData.prediction_score || 0) * 100),
      bitrateTrend: "stable",
      droppedFramesTrend: healthData.dropped_frames > 20 ? "up" : "stable",
      predictionTrend: "stable",
      predictions,
    };

    return Response.json(responseData);
  } catch (error) {
    console.error("Error fetching stream health:", error);
    return Response.json(
      { error: "Failed to fetch stream health data" },
      { status: 500 },
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      streamId,
      cpuUsage,
      gpuUsage,
      memoryUsage,
      networkLatency,
      bitrate,
      droppedFrames,
    } = body;

    // Calculate health status
    let healthStatus = "healthy";
    if (cpuUsage > 80 || gpuUsage > 90 || droppedFrames > 50) {
      healthStatus = "warning";
    }
    if (cpuUsage > 95 || gpuUsage > 95 || droppedFrames > 100) {
      healthStatus = "critical";
    }

    // Calculate prediction score (inverse of problems)
    const predictionScore =
      1 - (cpuUsage / 100 + gpuUsage / 100 + droppedFrames / 200) / 3;

    const result = await sql`
      INSERT INTO stream_health_metrics 
        (stream_id, cpu_usage, gpu_usage, memory_usage, network_latency, 
         bitrate, dropped_frames, health_status, prediction_score)
      VALUES 
        (${streamId}, ${cpuUsage}, ${gpuUsage}, ${memoryUsage}, ${networkLatency},
         ${bitrate}, ${droppedFrames}, ${healthStatus}, ${predictionScore})
      RETURNING *
    `;

    return Response.json({ success: true, data: result[0] });
  } catch (error) {
    console.error("Error updating stream health:", error);
    return Response.json(
      { error: "Failed to update stream health" },
      { status: 500 },
    );
  }
}
