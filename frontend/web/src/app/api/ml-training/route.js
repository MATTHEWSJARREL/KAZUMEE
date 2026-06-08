export async function GET(request) {
  return Response.json(
    {
      error:
        "Deprecated route. Use backend /api/ml-training through apiFetch.",
      simulated: false,
    },
    { status: 410 },
  );
}

export async function POST(request) {
  return Response.json(
    {
      error:
        "Deprecated route. Use backend /api/ml-training through apiFetch.",
      simulated: false,
    },
    { status: 410 },
  );
}
