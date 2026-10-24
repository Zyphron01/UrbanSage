"use client";

import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(onChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

/**
 * Returns true if the client environment prefers reduced motion.
 * SSR-safe: returns false during server rendering to prevent hydration mismatch.
 */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => (typeof window !== "undefined" ? window.matchMedia(QUERY).matches : false),
    () => false
  );
}
