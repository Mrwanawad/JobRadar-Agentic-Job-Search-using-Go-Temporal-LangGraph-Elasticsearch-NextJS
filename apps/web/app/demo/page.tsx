"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { SignInButtons } from "@/components/sign-in";
import { Turnstile } from "@/components/turnstile";
import { fetchMe, type Me } from "@/lib/site";
import { pdfText } from "@/lib/pdf";
import { REGIONS, SENIORITY } from "@/lib/demo-form";

const list = (s: string) =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

export default function DemoPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [cv, setCV] = useState("");
  const [cvNote, setCVNote] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const onToken = useCallback((t: string) => setToken(t), []);

  useEffect(() => {
    fetchMe()
      .then(setMe)
      .catch(() => setError("Could not reach the server."));
  }, []);

  if (!me) return <p className="text-muted">{error || "Loading…"}</p>;

  if (!me.user) {
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-semibold">Run JobRadar on your CV</h1>
        <p className="text-muted">
          Sign in so each account gets one demo run. Only your account id is kept, to enforce that limit.
        </p>
        <SignInButtons devLogin={me.dev_login} />
      </div>
    );
  }

  if (me.run) {
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-semibold">You already have a demo run</h1>
        <Link href="/run" className="btn-primary">
          See your results
        </Link>
      </div>
    );
  }

  async function onFile(f: File | undefined) {
    if (!f) return;
    setCVNote("Reading PDF…");
    try {
      const text = await pdfText(f);
      setCV(text);
      setCVNote(`${f.name}: ${text.length.toLocaleString()} characters extracted. Edit below if needed.`);
    } catch {
      setCVNote("Could not read that PDF. Paste the text instead.");
    }
  }

  async function submit(fd: FormData) {
    setBusy(true);
    setError("");
    const form = {
      name: String(fd.get("name") || "Candidate"),
      base: String(fd.get("base")),
      target_titles: list(String(fd.get("titles"))),
      seniority: String(fd.get("seniority")),
      remote_regions: fd.getAll("regions").map(String),
      onsite_locations: list(String(fd.get("onsite"))),
      needs_sponsorship: fd.get("sponsorship") === "on",
      skills: list(String(fd.get("skills"))),
    };
    const res = await fetch("/api/demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ form, cv_text: cv, turnstile: token }),
    });
    if (res.ok) return router.push("/run");
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    setError(body.error ?? `Request failed (${res.status})`);
    setBusy(false);
  }

  return (
    <form action={submit} className="grid max-w-3xl gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Run JobRadar on your CV</h1>
        <p className="mt-1 text-sm text-muted">
          Signed in as {me.user.name}. One run per account; results are deleted after 24 hours.
        </p>
        {me.pending && (
          <p className="mt-2 text-sm text-warn">
            Your profile is saved but the run did not start last time. Submit again to retry; the
            saved profile is used.
          </p>
        )}
      </div>

      <section className="grid gap-4 sm:grid-cols-2">
        <Field label="Name (signs the drafts)">
          <input name="name" className="field" maxLength={80} placeholder="Jane Doe" />
        </Field>
        <Field label="Where you live *">
          <input name="base" className="field" required maxLength={80} placeholder="Cairo, Egypt" />
        </Field>
        <Field label="Target titles, comma separated *">
          <input name="titles" className="field" required placeholder="AI Engineer, ML Engineer" />
        </Field>
        <Field label="Seniority">
          <select name="seniority" className="field" defaultValue="senior">
            {SENIORITY.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <Field label="On-site cities you would accept">
          <input name="onsite" className="field" placeholder="Dubai, Berlin" />
        </Field>
        <Field label="Key skills">
          <input name="skills" className="field" placeholder="python, llm, rag, fastapi" />
        </Field>
      </section>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Remote roles open to</legend>
        <div className="flex flex-wrap gap-3">
          {REGIONS.map((r) => (
            <label key={r} className="flex items-center gap-2 text-sm">
              <input type="checkbox" name="regions" value={r} defaultChecked={r === "worldwide"} /> {r}
            </label>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="sponsorship" /> I need visa sponsorship for roles abroad
        </label>
      </fieldset>

      <section className="space-y-2">
        <Field label="CV (the PDF is read in your browser; only its text is sent)">
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => onFile(e.target.files?.[0])}
            className="text-sm"
          />
        </Field>
        {cvNote && <p className="text-xs text-muted">{cvNote}</p>}
        <textarea
          value={cv}
          onChange={(e) => setCV(e.target.value)}
          className="field h-48 font-mono text-xs"
          placeholder="…or paste your CV text here"
          maxLength={60000}
        />
      </section>

      <Turnstile siteKey={me.turnstile_site_key} onToken={onToken} />
      {error && <p className="text-sm text-warn">{error}</p>}
      <div>
        <button type="submit" className="btn-primary" disabled={busy || !token || cv.trim().length < 200}>
          {busy ? "Starting…" : "Start my run"}
        </button>
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="font-medium">{label}</span>
      {children}
    </label>
  );
}
