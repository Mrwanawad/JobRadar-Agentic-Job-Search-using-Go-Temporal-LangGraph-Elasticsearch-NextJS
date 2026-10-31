// Plain <a>, not <Link>: OAuth starts with a full-page redirect, and <Link> prefetching would
// hit the route and overwrite the state cookie.
/* eslint-disable @next/next/no-html-link-for-pages */
export function SignInButtons({ devLogin = false }: { devLogin?: boolean }) {
  return (
    <div className="flex flex-wrap gap-3">
      <a href="/api/auth/github" className="btn-primary">Continue with GitHub</a>
      <a href="/api/auth/google" className="btn-ghost">Continue with Google</a>
      {devLogin && <a href="/api/auth/dev" className="btn-ghost">Local test sign-in</a>}
    </div>
  );
}
