import sql from "@/app/api/utils/sql";

export async function POST(request, { params }) {
  try {
    const { id } = params;

    const result = await sql`
      UPDATE command_queue
      SET status = 'executed', executed_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;

    if (result.length === 0) {
      return Response.json({ error: "Command not found" }, { status: 404 });
    }

    return Response.json({ success: true, command: result[0] });
  } catch (error) {
    console.error("Error executing command:", error);
    return Response.json(
      { error: "Failed to execute command" },
      { status: 500 },
    );
  }
}
