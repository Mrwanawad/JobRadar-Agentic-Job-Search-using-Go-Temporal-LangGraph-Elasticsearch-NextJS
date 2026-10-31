import type { NextConfig } from "next";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

const nextConfig: NextConfig = {
  // cacheComponents/partialPrefetching stay off: they hang on the Workers runtime
  // (OpenNext 1.20 warns about its setTimeout), and every page here is static or per-user.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

// Exposes wrangler bindings (D1, vars, .dev.vars secrets) to `next dev`.
initOpenNextCloudflareForDev();
