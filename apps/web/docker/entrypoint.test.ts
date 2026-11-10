import { spawnSync } from "node:child_process";
import { chmod, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vite-plus/test";

// The container entrypoint decides where secrets come from before the server starts.
// These run the real script with a fake `infisical` CLI on PATH, so no network or secrets
// are involved. The fake records its arguments and, for `run`, executes the wrapped
// command. Mirrors apps/api/tests/test_entrypoint.py so both images stay in step.

const ENTRYPOINT = new URL("./entrypoint.sh", import.meta.url);

const FAKE_INFISICAL = `#!/bin/sh
echo "$*" >> "$FAKE_LOG"
case "$1" in
  login)
    [ "\${FAKE_LOGIN_FAILS:-}" = 1 ] && exit 1
    echo fake-token ;;
  run)
    while [ "$1" != "--" ]; do shift; done
    shift
    exec "$@" ;;
esac
`;

const BOOTSTRAP = {
  INFISICAL_PROJECT_ID: "proj-123",
  INFISICAL_CLIENT_ID: "client-abc",
  INFISICAL_CLIENT_SECRET: "S3cretClient",
  INFISICAL_ENV: "staging",
  INFISICAL_API_URL: "https://infisical.example.test",
} as const;

type Run = {
  status: number;
  stdout: string;
  stderr: string;
  calls: string[];
};

async function run(
  env: Record<string, string>,
  command: readonly string[] = ["env"],
): Promise<Run> {
  const dir = await mkdtemp(path.join(tmpdir(), "web-entrypoint-"));
  const binDir = path.join(dir, "bin");
  await mkdir(binDir);
  const fake = path.join(binDir, "infisical");
  await writeFile(fake, FAKE_INFISICAL, "utf8");
  await chmod(fake, 0o755);
  // Normalise line endings so the test also runs from a CRLF (autocrlf) checkout.
  const script = path.join(dir, "entrypoint.sh");
  const source = await readFile(ENTRYPOINT, "utf8");
  await writeFile(script, source.replace(/\r\n/g, "\n"), "utf8");
  const log = path.join(dir, "infisical.log");

  const result = spawnSync("sh", [script, ...command], {
    env: { PATH: `${binDir}${path.delimiter}/usr/bin:/bin`, FAKE_LOG: log, ...env },
    encoding: "utf8",
    timeout: 10_000,
  });
  const calls = await readFile(log, "utf8")
    .then((text) => text.split("\n").filter(Boolean))
    .catch(() => []);
  return {
    status: result.status ?? -1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
    calls,
  };
}

describe("web container entrypoint", () => {
  it("without Infisical it runs the command with the platform variables", async () => {
    const result = await run({ API_URL: "https://api.example.test", AUTH_MODE: "logto" });

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("API_URL=https://api.example.test");
    expect(result.stderr).toContain("platform environment variables");
    expect(result.calls).toEqual([]);
  });

  it("with Infisical it wraps the command in infisical run", async () => {
    const result = await run(BOOTSTRAP);

    expect(result.status).toBe(0);
    const [login, cliRun] = result.calls;
    expect(login.startsWith("login --method=universal-auth")).toBe(true);
    expect(login).toContain("--domain=https://infisical.example.test");
    expect(cliRun).toContain("--projectId=proj-123");
    expect(cliRun).toContain("--env=staging");
    expect(cliRun).toContain("--token=fake-token");
    expect(result.stderr).toContain("env=staging");
  });

  it("the server never sees the long-lived client credentials", async () => {
    const result = await run(BOOTSTRAP);

    expect(result.status).toBe(0);
    expect(result.stdout).not.toContain("S3cretClient");
    expect(result.stdout).not.toContain("INFISICAL_CLIENT_ID");
    expect(result.stderr).not.toContain("S3cretClient");
  });

  it("the server never sees the access token", async () => {
    const result = await run(BOOTSTRAP);

    expect(result.status).toBe(0);
    expect(result.stdout).not.toContain("INFISICAL_TOKEN");
    expect(result.stdout).not.toContain("fake-token");
  });

  it("an inherited Infisical token is not passed to the server", async () => {
    const result = await run({ ...BOOTSTRAP, INFISICAL_TOKEN: "inherited-token" });

    expect(result.status).toBe(0);
    expect(result.stdout).not.toContain("INFISICAL_TOKEN");
    expect(result.stdout).not.toContain("inherited-token");
  });

  it("partly configured Infisical fails instead of falling back", async () => {
    const env = Object.fromEntries(
      Object.entries(BOOTSTRAP).filter(([key]) => key !== "INFISICAL_CLIENT_SECRET"),
    );

    const result = await run(env);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain("INFISICAL_CLIENT_SECRET");
    expect(result.calls).toEqual([]);
  });

  it.each(["dev", "development", "local"])("a development slug is refused (%s)", async (slug) => {
    const result = await run({ ...BOOTSTRAP, INFISICAL_ENV: slug });

    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain(`INFISICAL_ENV=${slug}`);
    expect(result.calls).toEqual([]);
  });

  it("a development slug can be allowed explicitly", async () => {
    const result = await run({
      ...BOOTSTRAP,
      INFISICAL_ENV: "dev",
      INFISICAL_ALLOW_DEV_ENV: "true",
    });

    expect(result.status).toBe(0);
    expect(result.calls[1]).toContain("--env=dev");
  });

  it("the universal-auth and domain aliases are accepted", async () => {
    const result = await run({
      INFISICAL_PROJECT_ID: "proj-123",
      INFISICAL_UNIVERSAL_AUTH_CLIENT_ID: "client-abc",
      INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET: "S3cretClient",
      INFISICAL_ENV: "prod",
      INFISICAL_DOMAIN: "https://alias.example.test",
    });

    expect(result.status).toBe(0);
    expect(result.stdout).not.toContain("S3cretClient");
    expect(result.calls[0]).toContain("--domain=https://alias.example.test");
  });

  it("a failed login stops the container", async () => {
    const result = await run({ ...BOOTSTRAP, FAKE_LOGIN_FAILS: "1" });

    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain("login failed");
    expect(result.calls).toHaveLength(1);
  });
});
