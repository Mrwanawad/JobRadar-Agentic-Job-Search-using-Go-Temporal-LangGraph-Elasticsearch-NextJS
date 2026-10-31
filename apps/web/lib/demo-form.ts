import { z } from "zod";

// Mirrors jobradar/agent/profiles.py DemoForm; the agent re-validates it.
const item = z.string().trim().min(1).max(60);

export const REGIONS = ["worldwide", "emea", "mena", "europe", "americas", "apac"] as const;
export const SENIORITY = ["junior", "mid", "senior", "lead"] as const;

export const DemoForm = z.object({
  name: z.string().trim().min(1).max(80).default("Candidate"),
  base: z.string().trim().min(2).max(80),
  target_titles: z.array(item).min(1).max(6),
  seniority: z.enum(SENIORITY).default("senior"),
  remote_regions: z.array(z.enum(REGIONS)).max(6).default(["worldwide"]),
  onsite_locations: z.array(item).max(8).default([]),
  needs_sponsorship: z.boolean().default(false),
  skills: z.array(item).max(20).default([]),
});

export const DemoRequest = z.object({
  form: DemoForm,
  cv_text: z.string().trim().min(200, "CV text is too short (200+ characters)").max(60_000),
  turnstile: z.string().min(1),
});

export type DemoFormT = z.infer<typeof DemoForm>;
