import sql from "@/app/api/utils/sql";

export async function POST(request, { params }) {
  try {
    const { id } = params;
    const body = await request.json();
    const { feedback } = body;

    if (!feedback || !["approved", "rejected"].includes(feedback)) {
      return Response.json(
        { error: "Invalid feedback. Must be 'approved' or 'rejected'" },
        { status: 400 },
      );
    }

    const result = await sql`
      UPDATE moderation_events 
      SET feedback = ${feedback}, reviewed = true
      WHERE id = ${id}
      RETURNING *
    `;

    if (result.length === 0) {
      return Response.json(
        { error: "Moderation event not found" },
        { status: 404 },
      );
    }

    // Update ML learning data based on feedback
    const event = result[0];
    const feedbackScore = feedback === "approved" ? 1 : -1;

    await sql`
      INSERT INTO ml_learning_data 
        (streamer_id, data_type, category, content, feedback_score, confidence_score)
      VALUES 
        (${event.streamer_id}, 'moderation_feedback', 'community_pattern',
         ${JSON.stringify({
           event_type: event.event_type,
           severity: event.severity,
           action: event.action_taken,
           feedback: feedback,
         })}, ${feedbackScore}, 0.85)
    `;

    return Response.json({ success: true, event: result[0] });
  } catch (error) {
    console.error("Error submitting feedback:", error);
    return Response.json(
      { error: "Failed to submit feedback" },
      { status: 500 },
    );
  }
}
