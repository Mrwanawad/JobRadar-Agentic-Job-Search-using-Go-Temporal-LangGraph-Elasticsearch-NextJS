import { getUser } from "@/lib/session";
import { findRun } from "@/lib/db";
import { gateway } from "@/lib/gateway";

// Relays the gateway's Server-Sent Events for the caller's own run only.
export async function GET(req: Request, ctx: RouteContext<"/api/runs/[id]/events">) {
  const { id } = await ctx.params;
  const user = await getUser();
  const run = user && (await findRun(user.id));
  if (!run || run.workflow_id !== id) return new Response("not found", { status: 404 });

  const upstream = await gateway(`/v1/runs/${encodeURIComponent(id)}/events`, { signal: req.signal });
  if (!upstream.ok || !upstream.body) return new Response("gateway unavailable", { status: 502 });
  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive" },
  });
}
