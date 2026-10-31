"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    turnstile?: {
      render: (
        el: HTMLElement,
        opts: { sitekey: string; callback: (t: string) => void; "expired-callback": () => void },
      ) => string;
      remove: (id: string) => void;
    };
  }
}

const SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

export function Turnstile({ siteKey, onToken }: { siteKey: string; onToken: (t: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let id: string | undefined;
    const mount = () => {
      if (ref.current && window.turnstile) {
        id = window.turnstile.render(ref.current, {
          sitekey: siteKey,
          callback: onToken,
          "expired-callback": () => onToken(""),
        });
      }
    };
    if (window.turnstile) mount();
    else {
      let s = document.querySelector<HTMLScriptElement>(`script[src="${SRC}"]`);
      if (!s) {
        s = document.createElement("script");
        s.src = SRC;
        s.async = true;
        document.head.appendChild(s);
      }
      s.addEventListener("load", mount, { once: true });
    }
    return () => {
      if (id) window.turnstile?.remove(id);
    };
  }, [siteKey, onToken]);

  return <div ref={ref} />;
}
