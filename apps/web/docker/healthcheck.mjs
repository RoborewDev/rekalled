// Container health check: exit 0 if the web server answers 2xx on /, else 1.
// Used by the Dockerfile HEALTHCHECK and by Coolify's CMD health check. It is a file rather
// than an inline `node -e` because Coolify rejects quotes and brackets in health check
// commands. Node's built-in fetch, so the slim runtime image needs no curl or wget.

// Same port resolution as Nitro's node-server preset: NITRO_PORT wins over PORT, and an
// unset, empty or unparseable value falls back to 3000.
const parsedPort = Number.parseInt(process.env.NITRO_PORT ?? process.env.PORT ?? "");
const port = Number.isNaN(parsedPort) ? 3000 : parsedPort;

try {
  const response = await fetch(`http://127.0.0.1:${port}/`, {
    signal: AbortSignal.timeout(4000),
  });
  process.exit(response.ok ? 0 : 1);
} catch {
  process.exit(1);
}
