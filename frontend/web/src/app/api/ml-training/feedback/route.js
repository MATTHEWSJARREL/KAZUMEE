export async function POST(request) {
  return Response.json(
    {
      error:
        "Deprecated route. Use backend /api/ml-training/feedback through apiFetch.",
      simulated: false,
    },
    { status: 410 },
  );
}
