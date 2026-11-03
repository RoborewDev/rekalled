# syntax=docker/dockerfile:1.7
# Rekalled API image. One image is built per commit on main and promoted unchanged
# from staging to production: nothing environment-specific is baked in here.
# Build context: apps/api  (docker build -f apps/api/Dockerfile apps/api)

ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------------------
# Stage 1: resolve and install dependencies into /app/.venv with uv
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

# uv is copied from its official image, pinned, so builds are reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1

WORKDIR /app

# Dependencies first, in their own layer: this only rebuilds when uv.lock changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# ---------------------------------------------------------------------------
# Stage 2: Infisical CLI, downloaded and checksum-verified (optional at runtime)
# ---------------------------------------------------------------------------
FROM debian:trixie-slim AS infisical
ARG INFISICAL_VERSION=0.44.12
ARG INFISICAL_SHA256_AMD64=82cad3d11fb34e9a90772a803e538a2bc8e5dfe99a8b135fa352b9f0eae2ae9a
ARG INFISICAL_SHA256_ARM64=03f45146e1769cbee33aa4a00bb277ab9d7d953eb7cd026462578720d7d98d72
ARG TARGETARCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && case "${TARGETARCH:-amd64}" in \
    amd64) sum="${INFISICAL_SHA256_AMD64}" ;; \
    arm64) sum="${INFISICAL_SHA256_ARM64}" ;; \
    *) echo "unsupported arch ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl -fsSL -o /tmp/infisical.tgz \
    "https://github.com/Infisical/cli/releases/download/v${INFISICAL_VERSION}/cli_${INFISICAL_VERSION}_linux_${TARGETARCH:-amd64}.tar.gz" \
    && echo "${sum}  /tmp/infisical.tgz" | sha256sum -c - \
    && tar -xzf /tmp/infisical.tgz -C /usr/local/bin infisical \
    && /usr/local/bin/infisical --version

# ---------------------------------------------------------------------------
# Stage 3: runtime. No uv, no compilers, no dev dependencies, non-root user.
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

# Which commit this image was built from. Reported by /v1/health (Settings.git_sha).
ARG GIT_SHA=local
LABEL org.opencontainers.image.title="rekalled-api" \
    org.opencontainers.image.revision="${GIT_SHA}"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=infisical /usr/local/bin/infisical /usr/local/bin/infisical
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_SHA=${GIT_SHA} \
    PORT=8000

WORKDIR /app
# Numeric UID/GID: resolvable even where the name isn't (hadolint DL3066).
USER 10001
EXPOSE 8000

# Coolify waits for this before switching traffic (rolling update), and keeps the old
# container if it never passes. start-period covers migrations running at start-up.
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/v1/health\", timeout=4)"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["/app/docker/start.sh"]
