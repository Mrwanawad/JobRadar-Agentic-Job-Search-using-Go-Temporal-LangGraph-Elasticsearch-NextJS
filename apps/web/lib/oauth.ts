import "server-only";
import { GitHub, Google, decodeIdToken } from "arctic";
import type { OAuth2Tokens } from "arctic";
import { env } from "./env";
import type { User } from "./session";

export type Provider = "github" | "google";

export function isProvider(p: string): p is Provider {
  return p === "github" || p === "google";
}

async function redirectURI(p: Provider) {
  return `${(await env()).APP_URL}/api/auth/${p}/callback`;
}

export async function github() {
  const e = await env();
  return new GitHub(e.GITHUB_CLIENT_ID, e.GITHUB_CLIENT_SECRET, await redirectURI("github"));
}

export async function google() {
  const e = await env();
  return new Google(e.GOOGLE_CLIENT_ID, e.GOOGLE_CLIENT_SECRET, await redirectURI("google"));
}

export async function githubUser(tokens: OAuth2Tokens): Promise<User> {
  const res = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${tokens.accessToken()}`,
      "User-Agent": "jobradar-web",
      Accept: "application/vnd.github+json",
    },
  });
  if (!res.ok) throw new Error(`github /user: ${res.status}`);
  const u = (await res.json()) as { id: number; login: string; name: string | null; avatar_url: string };
  return { id: `github:${u.id}`, name: u.name || u.login, avatar: u.avatar_url };
}

export function googleUser(tokens: OAuth2Tokens): User {
  const c = decodeIdToken(tokens.idToken()) as { sub: string; name?: string; email?: string; picture?: string };
  return { id: `google:${c.sub}`, name: c.name || c.email || "Google user", avatar: c.picture };
}
