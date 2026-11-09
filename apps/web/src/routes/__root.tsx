import {
  HeadContent,
  Link,
  Outlet,
  Scripts,
  createRootRouteWithContext,
  useLocation,
} from "@tanstack/react-router";
import { useQuery, type QueryClient } from "@tanstack/react-query";
import { useLayoutEffect, useMemo, useRef, type ReactNode } from "react";

import { AuthProvider, RequireAuth, useAuth } from "#/auth";
import { configureApi } from "#/lib/api";
import { getRuntimeConfig } from "#/lib/runtime-config";
import appCss from "../styles.css?url";

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Rekalled" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootDocument,
  component: App,
});

// Server-rendered HTML shell. Nothing here touches auth or data.
function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

// Client-only (defaultSsr: false): auth → API client → layout.
function App() {
  return (
    <AuthProvider>
      <ApiClient>
        <Layout />
      </ApiClient>
    </AuthProvider>
  );
}

function ApiClient({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const latest = useRef(auth);
  // A layout effect keeps the ref current after every commit; writing it during render can
  // leave it pointing at a render React discarded.
  useLayoutEffect(() => {
    latest.current = auth;
  });

  // Read the API origin from the web server so it is not baked into this bundle.
  const config = useQuery({
    queryKey: ["runtime-config"],
    queryFn: () => getRuntimeConfig(),
    staleTime: Infinity,
  });

  // Configure once, before any child query runs; the ref always points at the current auth
  // state. Configuring twice is harmless: setConfig merges rather than replacing the client.
  useMemo(() => {
    if (!config.data) return;
    configureApi(config.data.apiUrl, {
      getAccessToken: (options) => latest.current.getAccessToken(options),
      signIn: (returnTo) => latest.current.signIn(returnTo),
    });
  }, [config.data]);

  if (config.isError) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p role="alert" className="text-sm text-red">
          Could not load the app configuration. Reload the page to try again.
        </p>
      </main>
    );
  }
  return config.data ? children : null;
}

function Layout() {
  const { pathname } = useLocation();
  if (pathname === "/callback") return <Outlet />;

  return (
    <RequireAuth returnTo={pathname}>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-8">
        <Outlet />
      </main>
    </RequireAuth>
  );
}

function Header() {
  const auth = useAuth();
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
        <Link to="/" className="font-display text-xl font-semibold">
          Rekalled
        </Link>
        <div className="flex items-center gap-3 text-sm text-ink-soft">
          <span>{auth.user?.name}</span>
          <button className="underline" onClick={auth.signOut}>
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
