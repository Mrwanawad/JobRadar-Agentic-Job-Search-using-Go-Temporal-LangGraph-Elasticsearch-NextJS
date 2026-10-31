// Bindings and secrets from wrangler.jsonc / .dev.vars.
interface CloudflareEnv {
  DB: D1Database;
  APP_URL: string;
  REPO_URL: string;
  TURNSTILE_SITE_KEY: string;
  SESSION_SECRET: string;
  GATEWAY_URL: string;
  GATEWAY_TOKEN: string;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  TURNSTILE_SECRET_KEY: string;
  CF_ACCESS_CLIENT_ID?: string;
  CF_ACCESS_CLIENT_SECRET?: string;
}
