"use client";

import { useEffect, useState } from "react";
import { fetchMe, type Me } from "@/lib/site";

export function UserMenu() {
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    fetchMe().then(setMe).catch(() => setMe(null));
  }, []);

  if (!me?.user) return null;
  return (
    <span className="flex items-center gap-2">
      {/* eslint-disable-next-line @next/next/no-img-element -- tiny third-party avatar */}
      {me.user.avatar && <img src={me.user.avatar} alt="" className="h-6 w-6 rounded-full" />}
      <button
        className="text-muted hover:text-foreground"
        onClick={async () => {
          await fetch("/api/auth/logout", { method: "POST" });
          // Full reload so every component drops the signed-in state.
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          location.href = "/";
        }}
      >
        Sign out
      </button>
    </span>
  );
}
