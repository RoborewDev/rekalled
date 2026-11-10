import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vite-plus/test";

// Architecture rule from the spec: only src/auth/ may know about Logto.
it("no file outside src/auth imports @logto/react", () => {
  const src = join(import.meta.dirname, "..");
  const offenders = readdirSync(src, { recursive: true, encoding: "utf8" })
    // readdirSync returns backslashes on Windows; compare with posix-style paths everywhere.
    .map((file) => file.replaceAll("\\", "/"))
    .filter((file) => /\.(?:[cm]?[jt]sx?)$/.test(file) && !file.startsWith("auth/"))
    .filter((file) => readFileSync(join(src, file), "utf8").includes("@logto/react"));

  expect(offenders).toEqual([]);
});
