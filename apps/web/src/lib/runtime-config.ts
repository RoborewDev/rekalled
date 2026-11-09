import { createServerFn } from "@tanstack/react-start";
import { resolveRuntimeConfig, type RuntimeConfig } from "./runtime-env";

/**
 * The API origin and auth mode differ between environments, so they are read from the web
 * server's environment at request time instead of being baked into the bundle by Vite. That
 * keeps one image valid for every environment.
 */
export const getRuntimeConfig = createServerFn({ method: "GET" }).handler((): RuntimeConfig =>
  resolveRuntimeConfig(process.env),
);
