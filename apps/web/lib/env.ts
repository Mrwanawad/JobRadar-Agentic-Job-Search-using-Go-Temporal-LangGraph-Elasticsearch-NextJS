import "server-only";
import { getCloudflareContext } from "@opennextjs/cloudflare";

export async function env(): Promise<CloudflareEnv> {
  return (await getCloudflareContext({ async: true })).env;
}

// Mutable 302 (Response.redirect's headers are immutable, so cookies set via cookies() could not be merged).
export function redirectTo(location: string): Response {
  return new Response(null, { status: 302, headers: { Location: location } });
}
