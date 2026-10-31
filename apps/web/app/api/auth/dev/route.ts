import { setSession } from "@/lib/session";
import { env, redirectTo } from "@/lib/env";

// Local testing without OAuth apps. Works only when DEV_LOGIN=1 and the app runs on
// localhost; production never sets DEV_LOGIN. Each sign-in is a fresh account, so the
// one-demo-run limit can be tested repeatedly.
export async function GET(req: Request) {
  const e = await env();
  const host = new URL(req.url).hostname;
  if (e.DEV_LOGIN !== "1" || (host !== "localhost" && host !== "127.0.0.1")) {
    return new Response("not found", { status: 404 });
  }
  await setSession({ id: `dev:${crypto.randomUUID()}`, name: "Local Tester" });
  return redirectTo(`${e.APP_URL}/demo`);
}
