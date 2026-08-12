import sql from "@/app/api/utils/sql";
import { getStreamerIdFromRequest } from "@/app/api/utils/getStreamerIdFromRequest";

export async function GET(request) {
  try {
    const streamerId = await getStreamerIdFromRequest(request);

    const profile = await sql`
      SELECT * FROM streamer_profiles
      WHERE streamer_id = ${streamerId}
      LIMIT 1
    `;

    const streamer = await sql`
      SELECT * FROM streamers
      WHERE id = ${streamerId}
      LIMIT 1
    `;

    if (profile.length === 0) {
      // Return default settings
      return Response.json({
        profile: {
          displayName: streamer[0]?.display_name || "Streamer",
        },
        voice: {
          model: "standard",
          responseSpeed: 75,
          enabled: true,
        },
        moderation: {
          strictness: "medium",
          autoModerate: true,
          contextAware: true,
        },
        automation: {
          autoClipping: true,
          autoHighlights: true,
          sceneControl: false,
        },
      });
    }

    return Response.json({
      profile: {
        displayName: streamer[0]?.display_name || "Streamer",
      },
      voice: profile[0].voice_preferences || {
        model: "standard",
        responseSpeed: 75,
        enabled: true,
      },
      moderation: {
        strictness: profile[0].moderation_strictness || "medium",
        autoModerate: true,
        contextAware: true,
      },
      automation: {
        autoClipping: true,
        autoHighlights: true,
        sceneControl: false,
      },
    });
  } catch (error) {
    console.error("Error fetching settings:", error);
    return Response.json(
      { error: "Failed to fetch settings" },
      { status: 500 },
    );
  }
}

export async function PUT(request) {
  try {
    const streamerId = await getStreamerIdFromRequest(request);
    const body = await request.json();

    // Update streamer profile
    if (body.profile?.displayName) {
      await sql`
        UPDATE streamers
        SET display_name = ${body.profile.displayName}
        WHERE id = ${streamerId}
      `;
    }

    // Update or create streamer_profiles
    const existing = await sql`
      SELECT id FROM streamer_profiles WHERE streamer_id = ${streamerId}
    `;

    if (existing.length === 0) {
      await sql`
        INSERT INTO streamer_profiles 
          (streamer_id, moderation_strictness, voice_preferences)
        VALUES 
          (${streamerId}, ${body.moderation?.strictness || "medium"}, 
           ${JSON.stringify(body.voice || {})})
      `;
    } else {
      await sql`
        UPDATE streamer_profiles
        SET moderation_strictness = ${body.moderation?.strictness || "medium"},
            voice_preferences = ${JSON.stringify(body.voice || {})},
            updated_at = NOW()
        WHERE streamer_id = ${streamerId}
      `;
    }

    return Response.json({ success: true });
  } catch (error) {
    console.error("Error saving settings:", error);
    return Response.json({ error: "Failed to save settings" }, { status: 500 });
  }
}
