import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { getRuntimeConfig } from "./runtime-config";
import type { RuntimeConfig } from "./runtime-env";

const RuntimeConfigContext = createContext<RuntimeConfig | null>(null);

/** Fetch the runtime config once and gate the tree until it is available. */
export function RuntimeConfigProvider({ children }: { children: ReactNode }) {
  const config = useQuery({
    queryKey: ["runtime-config"],
    queryFn: () => getRuntimeConfig(),
    staleTime: Infinity,
  });

  if (config.isError) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p role="alert" className="text-sm text-red">
          Could not load the app configuration. Reload the page to try again.
        </p>
      </main>
    );
  }
  if (!config.data) return null;
  return (
    <RuntimeConfigContext.Provider value={config.data}>{children}</RuntimeConfigContext.Provider>
  );
}

export function useRuntimeConfig(): RuntimeConfig {
  const config = useContext(RuntimeConfigContext);
  if (!config) throw new Error("useRuntimeConfig must be used inside RuntimeConfigProvider");
  return config;
}
