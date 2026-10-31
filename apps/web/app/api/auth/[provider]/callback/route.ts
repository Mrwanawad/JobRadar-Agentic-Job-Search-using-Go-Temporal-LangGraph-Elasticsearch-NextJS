import { cookies } from "next/headers";
import { github, githubUser, google, googleUser, isProvider } from "@/lib/oauth";
import { setSession } from "@/lib/session";
import { env, redirectTo } from "@/lib/env";

export async function GET(req: Request, ctx: RouteContext<"/api/auth/[provider]/callback">) {
  const { provider } = await ctx.params;
  if (!isProvider(provider)) return new Response("unknown provider", { status: 404 });

  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const jar = await cookies();
  const expected = jar.get("oauth_state")?.value;
  const verifier = jar.get("oauth_verifier")?.value;
  jar.delete("oauth_state");
  jar.delete("oauth_verifier");

  const home = (await env()).APP_URL;
  if (!code || !state || state !== expected) return redirectTo(`${home}/?error=oauth_state`);

  try {
    const user =
      provider === "github"
        ? await githubUser(await (await github()).validateAuthorizationCode(code))
        : googleUser(await (await google()).validateAuthorizationCode(code, verifier ?? ""));
    await setSession(user);
  } catch (err) {
    console.error("oauth callback", provider, err);
    return redirectTo(`${home}/?error=oauth_failed`);
  }
  return redirectTo(`${home}/demo`);
}
