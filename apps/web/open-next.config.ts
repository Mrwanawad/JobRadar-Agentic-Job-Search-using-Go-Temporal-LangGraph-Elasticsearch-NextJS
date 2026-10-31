import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// No incremental cache: every page is either static or per-user.
export default defineCloudflareConfig();
