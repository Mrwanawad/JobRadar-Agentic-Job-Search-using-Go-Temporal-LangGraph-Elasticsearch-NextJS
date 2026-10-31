import Link from "next/link";
import { REPO_URL } from "@/lib/site";

const STEPS = [
  ["Fetch", "Go workers pull ~60 job boards and ATS feeds in parallel, as Temporal activities with retries."],
  ["Prefilter", "Title, seniority and location rules from your profile drop obvious misses before any LLM call."],
  ["Match", "Hybrid Elasticsearch search (BM25 + embeddings, fused with RRF) ranks what's left against your CV."],
  ["Score", "A LangGraph screening agent reads each top posting and returns a structured fit assessment."],
  ["Draft", "A writer/critic agent pair drafts outreach for the best fits, then waits for human approval."],
];

const STACK = ["Go", "Temporal", "Python", "LangGraph", "Elasticsearch", "Postgres", "OpenTelemetry", "Next.js", "Cloudflare"];

export default function Home() {
  return (
    <div className="space-y-16">
      <section className="space-y-6">
        <p className="font-mono text-xs uppercase tracking-widest text-accent">Agentic job search</p>
        <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Upload a CV. Get today&apos;s best-fit jobs, ranked and explained.
        </h1>
        <p className="max-w-2xl text-lg text-muted">
          JobRadar runs a durable pipeline over thousands of live postings: Go ingestion on Temporal, LangGraph agents for
          screening and drafting, and hybrid search in Elasticsearch. The demo runs the real pipeline on your CV.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/demo" className="btn-primary">Try the demo</Link>
          <a href={REPO_URL} className="btn-ghost">Read the code</a>
        </div>
        <ul className="flex flex-wrap gap-2 pt-2">
          {STACK.map((s) => (
            <li key={s} className="rounded-full border border-line px-3 py-1 font-mono text-xs text-muted">{s}</li>
          ))}
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">What happens in a run</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="rounded-lg border border-line bg-surface p-4">
              <p className="font-mono text-xs text-accent">0{i + 1}</p>
              <p className="mt-1 font-medium">{title}</p>
              <p className="mt-2 text-sm text-muted">{body}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
