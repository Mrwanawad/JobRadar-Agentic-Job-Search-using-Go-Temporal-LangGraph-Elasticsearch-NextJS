"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe, type Me } from "@/lib/site";

// protojson of jobradar.v1.RadarProgress (camelCase; zero fields may be omitted).
type Progress = {
  stage?: string;
  sourcesTotal?: number;
  sourcesDone?: number;
  fetched?: number;
  inserted?: number;
  candidates?: number;
  indexed?: number;
  matched?: number;
  scored?: number;
  drafted?: number;
  errors?: string[];
};

type Result = {
  job_uid: string;
  company: string;
  title: string;
  location: string;
  url: string;
  score: number | null;
  assessment: {
    reasons?: string[];
    red_flags?: string[];
    pitch_angle?: string;
    location_fit?: string;
    seniority_fit?: string;
  } | null;
  subject: string | null;
  body: string | null;
  draft_status: string | null;
};

const STAGES = [
  ["STAGE_FETCHING", "Fetching sources"],
  ["STAGE_PREFILTERING", "Prefiltering"],
  ["STAGE_INDEXING", "Indexing"],
  ["STAGE_MATCHING", "Hybrid matching"],
  ["STAGE_SCORING", "LLM scoring"],
  ["STAGE_DRAFTING", "Drafting"],
  ["STAGE_AWAITING_APPROVAL", "Ready for review"],
  ["STAGE_DONE", "Done"],
] as const;

export default function RunPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState("running");
  const [progress, setProgress] = useState<Progress>({});
  const [results, setResults] = useState<Result[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMe()
      .then(setMe)
      .catch(() => setError("Could not reach the server."));
  }, []);

  const workflowID = me?.run?.workflow_id;

  useEffect(() => {
    if (!workflowID) return;
    const loadResults = () =>
      fetch("/api/results", { cache: "no-store" })
        .then((r) => r.json() as Promise<{ results?: Result[] }>)
        .then((d) => setResults(d.results ?? []))
        .catch(() => setError("Could not load results."));

    const es = new EventSource(`/api/runs/${encodeURIComponent(workflowID)}/events`);
    es.onmessage = (e) => {
      const msg = JSON.parse(e.data) as { status: string; progress: Progress | null };
      setStatus(msg.status);
      if (msg.progress) setProgress(msg.progress);
      if (msg.progress?.scored) loadResults();
    };
    es.addEventListener("done", () => {
      es.close();
      loadResults();
    });
    es.onerror = () => {
      // The browser reconnects on its own; a run that already ended has nothing more to stream.
      if (es.readyState === EventSource.CLOSED) loadResults();
    };
    return () => es.close();
  }, [workflowID]);

  if (error) return <p className="text-warn">{error}</p>;
  if (!me) return <p className="text-muted">Loading…</p>;
  if (!me.run) {
    return (
      <div className="space-y-4">
        <p>No demo run on this account yet.</p>
        <Link href="/demo" className="btn-primary">
          Start one
        </Link>
      </div>
    );
  }

  const current = STAGES.findIndex(([s]) => s === progress.stage);
  const counters: [string, number | undefined][] = [
    ["sources", progress.sourcesDone],
    ["jobs fetched", progress.fetched],
    ["candidates", progress.candidates],
    ["matched", progress.matched],
    ["scored", progress.scored],
    ["drafts", progress.drafted],
  ];

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="text-2xl font-semibold">Your run</h1>
          <span className="font-mono text-xs text-muted">
            {workflowID} · {status}
          </span>
        </div>
        <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {STAGES.map(([key, label], i) => (
            <li
              key={key}
              className={`rounded-md border px-2 py-2 text-xs ${
                i < current || status !== "running"
                  ? "border-accent text-accent"
                  : i === current
                    ? "animate-pulse border-accent bg-accent text-accent-ink"
                    : "border-line text-muted"
              }`}
            >
              {label}
            </li>
          ))}
        </ol>
        <dl className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          {counters.map(([label, n]) => (
            <div key={label} className="rounded-lg border border-line bg-surface p-3">
              <dt className="text-xs text-muted">{label}</dt>
              <dd className="font-mono text-lg">{(n ?? 0).toLocaleString()}</dd>
            </div>
          ))}
        </dl>
        {!!progress.errors?.length && (
          <p className="text-xs text-warn">
            {progress.errors.length} source(s) failed; the run continued without them.
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Ranked jobs</h2>
        {results === null && <p className="text-sm text-muted">Scores appear here as the agent works.</p>}
        {results?.length === 0 && <p className="text-sm text-muted">No job scored yet.</p>}
        <ul className="space-y-3">
          {results?.map((r) => (
            <li key={r.job_uid} className="rounded-lg border border-line bg-surface p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <a href={r.url} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">
                    {r.title}
                  </a>
                  <p className="text-sm text-muted">
                    {r.company} · {r.location || "location not stated"}
                  </p>
                </div>
                <span className="font-mono text-2xl text-accent">{r.score?.toFixed(1) ?? "–"}</span>
              </div>
              {r.assessment?.pitch_angle && <p className="mt-3 text-sm">{r.assessment.pitch_angle}</p>}
              {!!r.assessment?.reasons?.length && (
                <ul className="mt-2 list-disc pl-5 text-sm text-muted">
                  {r.assessment.reasons.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )}
              {!!r.assessment?.red_flags?.length && (
                <p className="mt-2 text-xs text-warn">Watch out: {r.assessment.red_flags.join("; ")}</p>
              )}
              {r.body && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm text-accent">Draft application ({r.draft_status})</summary>
                  {r.subject && <p className="mt-2 text-sm font-medium">{r.subject}</p>}
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm">{r.body}</pre>
                </details>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
