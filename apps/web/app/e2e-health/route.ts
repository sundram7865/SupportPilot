export async function GET() {
  return Response.json({
    ok: true,
    service: "supportpilot-web",
  });
}