import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { expect, it } from "vite-plus/test";

// Architecture rule from the spec: only src/auth/ may know about Logto.
it("no file outside src/auth imports @logto/react", () => {
  const src = join(import.meta.dirname, "..");
  const offenders = readdirSync(src, { recursive: true, encoding: "utf8" })
    .filter((file) => /\.(ts|tsx)$/.test(file) && !file.startsWith("auth/"))
    .filter((file) => readFileSync(join(src, file), "utf8").includes("@logto/react"))
    .map((file) => relative(src, join(src, file)));

  expect(offenders).toEqual([]);
});
