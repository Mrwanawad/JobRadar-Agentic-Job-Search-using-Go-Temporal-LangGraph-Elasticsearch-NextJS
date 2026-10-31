import "server-only";
import { env } from "./env";

export async function verifyTurnstile(token: string, ip: string | null): Promise<boolean> {
  if (!token) return false;
  const body = new FormData();
  body.set("secret", (await env()).TURNSTILE_SECRET_KEY);
  body.set("response", token);
  if (ip) body.set("remoteip", ip);
  const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body });
  const out = (await res.json()) as { success: boolean };
  return out.success === true;
}
