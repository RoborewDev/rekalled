import { createCsrfMiddleware, createStart } from "@tanstack/react-start";

// Server functions are same-origin RPC endpoints, so reject cross-site requests. The app
// authenticates with bearer tokens rather than cookies, but this is cheap defence in depth.
const csrfMiddleware = createCsrfMiddleware({
  filter: (ctx) => ctx.handlerType === "serverFn",
});

// Everything in Rekalled is private and the auth SDK lives in the browser,
// so routes render on the client. Start still serves the HTML shell.
export const startInstance = createStart(() => ({
  defaultSsr: false,
  requestMiddleware: [csrfMiddleware],
}));
