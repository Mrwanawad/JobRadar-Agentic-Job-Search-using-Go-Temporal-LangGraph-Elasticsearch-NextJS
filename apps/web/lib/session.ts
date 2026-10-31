import "server-only";
import { cookies } from "next/headers";
import { SignJWT, jwtVerify } from "jose";
import { env } from "./env";

export type User = {
  id: string; // "github:<id>" | "google:<sub>": the demo quota key
  name: string;
  avatar?: string;
};

const COOKIE = "jr_session";
const MAX_AGE = 60 * 60 * 24 * 7;

async function key() {
  const secret = (await env()).SESSION_SECRET;
  if (!secret || secret.length < 32) throw new Error("SESSION_SECRET must be 32+ characters");
  return new TextEncoder().encode(secret);
}

export async function setSession(user: User) {
  const token = await new SignJWT({ name: user.name, avatar: user.avatar })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.id)
    .setIssuedAt()
    .setExpirationTime(`${MAX_AGE}s`)
    .sign(await key());
  (await cookies()).set(COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: MAX_AGE,
  });
}

export async function getUser(): Promise<User | null> {
  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, await key(), { algorithms: ["HS256"] });
    if (!payload.sub) return null;
    return {
      id: payload.sub,
      name: String(payload.name ?? ""),
      avatar: payload.avatar ? String(payload.avatar) : undefined,
    };
  } catch {
    return null;
  }
}

export async function clearSession() {
  (await cookies()).delete(COOKIE);
}
