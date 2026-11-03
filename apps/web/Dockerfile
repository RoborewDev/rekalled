# syntax=docker/dockerfile:1.7
# Rekalled web image (TanStack Start, Nitro node-server output).
# Built once per commit on main and promoted unchanged to production.
# Build context: apps/web  (docker build -f apps/web/Dockerfile apps/web)
#
# Parity rule: anything read via import.meta.env.VITE_* is inlined at BUILD time, so it is
# identical in staging and production. Never put a per-environment value in a VITE_ var;
# per-environment values must be read at runtime from process.env on the server.

ARG NODE_VERSION=24

# ---------------------------------------------------------------------------
# Stage 1: install and build
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION}-slim AS builder
ARG PNPM_VERSION=12.16.1
# hadolint ignore=DL3016
RUN npm install -g "pnpm@${PNPM_VERSION}" && pnpm --version
WORKDIR /app

# Lockfile first so the dependency layer is cached until it changes.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# ---------------------------------------------------------------------------
# Stage 2: runtime. .output is self-contained (Nitro bundles server deps), so no
# node_modules, no pnpm and no source code ship in this image.
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION}-slim AS runtime
ARG GIT_SHA=local
LABEL org.opencontainers.image.title="rekalled-web" \
      org.opencontainers.image.revision="${GIT_SHA}"

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    GIT_SHA=${GIT_SHA}

WORKDIR /app
COPY --from=builder --chown=node:node /app/.output ./.output
USER node
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

CMD ["node", ".output/server/index.mjs"]
