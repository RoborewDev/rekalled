import { createStart } from "@tanstack/react-start";

// Everything in Rekalled is private and the auth SDK lives in the browser,
// so routes render on the client. Start still serves the HTML shell.
export const startInstance = createStart(() => ({ defaultSsr: false }));
