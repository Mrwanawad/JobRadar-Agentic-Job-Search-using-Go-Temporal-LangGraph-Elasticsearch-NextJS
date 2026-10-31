import { getUser } from "@/lib/session";
import { findRun, saveProfile, setWorkflow } from "@/lib/db";
import { gatewayJSON } from "@/lib/gateway";
import { verifyTurnstile } from "@/lib/turnstile";
import { DemoRequest } from "@/lib/demo-form";

const err = (status: number, error: string) => Response.json({ error }, { status });

// Starts the visitor's one demo run: profile (CV text + form) then the Temporal workflow.
// If the workflow fails to start, the profile is kept and the next submit retries the start.
export async function POST(req: Request) {
  const user = await getUser();
  if (!user) return err(401, "sign in first");
  const existing = await findRun(user.id);
  if (existing?.workflow_id) return err(409, "this account already used its demo run");

  const parsed = DemoRequest.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return err(400, parsed.error.issues[0]?.message ?? "invalid form");
  const { form, cv_text, turnstile } = parsed.data;

  if (!(await verifyTurnstile(turnstile, req.headers.get("CF-Connecting-IP")))) {
    return err(403, "bot check failed, reload and try again");
  }

  let profileID = existing?.profile_id;
  if (!profileID) {
    const profile = await gatewayJSON<{ id?: string; error?: string }>("/v1/profiles", {
      method: "POST",
      body: JSON.stringify({ kind: "demo", owner: user.id, profile: form, cv_text }),
    });
    if (profile.status !== 201 || !profile.data.id) {
      return err(profile.status, profile.data.error ?? "could not create profile");
    }
    profileID = profile.data.id;
    await saveProfile(user.id, profileID);
  }

  const run = await gatewayJSON<{ workflow_id?: string; error?: string }>("/v1/runs", {
    method: "POST",
    body: JSON.stringify({ profile_id: profileID }),
  });
  if (run.status !== 202 || !run.data.workflow_id) {
    const msg = run.data.error ?? "could not start run";
    return err(run.status >= 500 ? 502 : run.status, `${msg}. Your profile is saved; submit again to retry.`);
  }

  await setWorkflow(user.id, run.data.workflow_id);
  return Response.json({ workflow_id: run.data.workflow_id }, { status: 202 });
}
