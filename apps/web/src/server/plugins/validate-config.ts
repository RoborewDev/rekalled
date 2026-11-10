import { resolveRuntimeConfig } from "../../lib/runtime-env";

/**
 * Fail at start-up, not on the first request. The runtime-config server function resolves
 * its values per request, so a missing value would otherwise leave the container healthy
 * while every page shows "Could not load the app configuration" — the health check only
 * sees `/`, which always serves the HTML shell. Resolving here crashes the server instead,
 * so the Docker health check fails and Coolify reports an unhealthy deployment.
 *
 * Local development passes by design: outside production the resolver falls back to the
 * local API and the dev adapter. Relative import because Nitro bundles this file with its
 * own resolver, which does not know the `#/*` package-import alias.
 */
export default function validateRuntimeConfig(): void {
  resolveRuntimeConfig(process.env);
}
