import { API_BASE } from "../../../config";

export async function POST(request) {
  try {
    const body = await request.json();
    const { command } = body;

    if (!command) {
      return Response.json({ error: "Command is required" }, { status: 400 });
    }

    // Forward command directly to FastAPI
    const backendResponse = await fetch(`${API_BASE}/commands/process`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: command }),
    });

    if (!backendResponse.ok) {
      const text = await backendResponse.text();
      throw new Error(`Backend error: ${text}`);
    }

    const data = await backendResponse.json();

    // Return backend result as-is
    return Response.json(data);
  } catch (error) {
    console.error("Error forwarding command:", error);
    return Response.json(
      { error: "Failed to execute command" },
      { status: 500 }
    );
  }
}
