import { cookies } from "next/headers";
import { generateCodeVerifier, generateState } from "arctic";
import { github, google, isProvider } from "@/lib/oauth";
import { redirectTo } from "@/lib/env";

const TEN_MINUTES = 600;

// Starts the OAuth flow: state (and the PKCE verifier for Google) ride in short-lived cookies.
export async function GET(_req: Request, ctx: RouteContext<"/api/auth/[provider]">) {
  const { provider } = await ctx.params;
  if (!isProvider(provider)) return new Response("unknown provider", { status: 404 });

  const jar = await cookies();
  const opts = { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax" as const, path: "/", maxAge: TEN_MINUTES };
  const state = generateState();
  jar.set("oauth_state", state, opts);

  let url: URL;
  if (provider === "github") {
    url = (await github()).createAuthorizationURL(state, []);
  } else {
    const verifier = generateCodeVerifier();
    jar.set("oauth_verifier", verifier, opts);
    url = (await google()).createAuthorizationURL(state, verifier, ["openid", "profile", "email"]);
  }
  return redirectTo(url.toString());
}
