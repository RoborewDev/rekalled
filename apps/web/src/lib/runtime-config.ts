import { createServerFn } from "@tanstack/react-start";

export type RuntimeConfig = { apiUrl: string };

/**
 * The API origin differs between staging and production, so it is read from the web
 * server's environment at request time (API_URL) instead of being baked into the bundle by
 * Vite. That keeps one image valid for every environment.
 */
export const getRuntimeConfig = createServerFn({ method: "GET" }).handler((): RuntimeConfig => {
  // Production must say where the API is; the local default only saves dev setup.
  const apiUrl =
    process.env.API_URL?.trim() ||
    (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
  if (!apiUrl) throw new Error("API_URL must be set for the web server");
  return { apiUrl };
});
