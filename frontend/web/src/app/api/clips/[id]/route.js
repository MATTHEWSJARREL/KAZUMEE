import sql from "@/app/api/utils/sql";

export async function GET(request, { params }) {
  try {
    const { id } = params;
    const result = await sql`
      SELECT * FROM clips WHERE id = ${id}
    `;

    if (result.length === 0) {
      return Response.json({ error: "Clip not found" }, { status: 404 });
    }

    return Response.json({ clip: result[0] });
  } catch (error) {
    console.error("Error fetching clip:", error);
    return Response.json({ error: "Failed to fetch clip" }, { status: 500 });
  }
}

export async function PUT(request, { params }) {
  try {
    const { id } = params;
    const body = await request.json();

    const updates = [];
    const values = [];
    let paramCount = 1;

    if (body.title !== undefined) {
      updates.push(`title = $${paramCount}`);
      values.push(body.title);
      paramCount++;
    }
    if (body.description !== undefined) {
      updates.push(`description = $${paramCount}`);
      values.push(body.description);
      paramCount++;
    }
    if (body.tags !== undefined) {
      updates.push(`tags = $${paramCount}`);
      values.push(body.tags);
      paramCount++;
    }
    if (body.performanceScore !== undefined) {
      updates.push(`performance_score = $${paramCount}`);
      values.push(body.performanceScore);
      paramCount++;
    }

    if (updates.length === 0) {
      return Response.json({ error: "No fields to update" }, { status: 400 });
    }

    values.push(id);
    const query = `UPDATE clips SET ${updates.join(", ")} WHERE id = $${paramCount} RETURNING *`;

    const result = await sql(query, values);

    if (result.length === 0) {
      return Response.json({ error: "Clip not found" }, { status: 404 });
    }

    return Response.json({ success: true, clip: result[0] });
  } catch (error) {
    console.error("Error updating clip:", error);
    return Response.json({ error: "Failed to update clip" }, { status: 500 });
  }
}

export async function DELETE(request, { params }) {
  try {
    const { id } = params;
    const result = await sql`
      DELETE FROM clips WHERE id = ${id} RETURNING *
    `;

    if (result.length === 0) {
      return Response.json({ error: "Clip not found" }, { status: 404 });
    }

    return Response.json({ success: true, message: "Clip deleted" });
  } catch (error) {
    console.error("Error deleting clip:", error);
    return Response.json({ error: "Failed to delete clip" }, { status: 500 });
  }
}
