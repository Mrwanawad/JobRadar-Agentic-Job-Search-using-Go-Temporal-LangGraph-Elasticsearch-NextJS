import "server-only";
import { env } from "./env";

// The gateway sits behind a Cloudflare Tunnel; only this worker holds its bearer token.
// When the tunnel hostname is also behind Cloudflare Access, the service token is added.
export async function gateway(path: string, init: RequestInit = {}): Promise<Response> {
  const e = await env();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${e.GATEWAY_TOKEN}`);
  if (init.body) headers.set("Content-Type", "application/json");
  if (e.CF_ACCESS_CLIENT_ID && e.CF_ACCESS_CLIENT_SECRET) {
    headers.set("CF-Access-Client-Id", e.CF_ACCESS_CLIENT_ID);
    headers.set("CF-Access-Client-Secret", e.CF_ACCESS_CLIENT_SECRET);
  }
  return fetch(`${e.GATEWAY_URL.replace(/\/$/, "")}${path}`, { ...init, headers });
}

export async function gatewayJSON<T>(path: string, init: RequestInit = {}): Promise<{ status: number; data: T }> {
  const res = await gateway(path, init);
  const data = (await res.json().catch(() => ({ error: `gateway returned ${res.status}` }))) as T;
  return { status: res.status, data };
}
