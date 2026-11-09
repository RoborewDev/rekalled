/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AUTH_MODE?: "dev" | "logto";
  readonly VITE_API_URL: string;
}
