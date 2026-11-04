"""The container entrypoint decides where secrets come from before the app starts.

These run the real script with a fake `infisical` CLI on PATH, so no network or secrets
are involved. The fake records its arguments and, for `run`, executes the wrapped command.
"""

import os
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "docker" / "entrypoint.sh"

FAKE_INFISICAL = """#!/bin/sh
echo "$*" >> "$FAKE_LOG"
case "$1" in
  login)
    [ "${FAKE_LOGIN_FAILS:-}" = 1 ] && exit 1
    echo fake-token ;;
  run)
    while [ "$1" != "--" ]; do shift; done
    shift
    exec "$@" ;;
esac
"""

BOOTSTRAP = {
    "INFISICAL_PROJECT_ID": "proj-123",
    "INFISICAL_CLIENT_ID": "client-abc",
    "INFISICAL_CLIENT_SECRET": "S3cretClient",
    "INFISICAL_ENV": "staging",
    "INFISICAL_API_URL": "https://infisical.example.test",
}


class Entrypoint:
    def __init__(self, tmp_path: Path) -> None:
        self.bin_dir = tmp_path / "bin"
        self.bin_dir.mkdir()
        fake = self.bin_dir / "infisical"
        fake.write_text(FAKE_INFISICAL)
        fake.chmod(0o755)
        # Normalise line endings so the test also runs from a CRLF (autocrlf) checkout.
        self.script = tmp_path / "entrypoint.sh"
        self.script.write_text(ENTRYPOINT.read_text().replace("\r\n", "\n"))
        self.log = tmp_path / "infisical.log"

    def run(self, env: dict[str, str], *command: str) -> subprocess.CompletedProcess[str]:
        base = {"PATH": f"{self.bin_dir}{os.pathsep}/usr/bin:/bin", "FAKE_LOG": str(self.log)}
        return subprocess.run(
            ["sh", str(self.script), *(command or ("env",))],
            env={**base, **env},
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def entrypoint(tmp_path: Path) -> Entrypoint:
    return Entrypoint(tmp_path)


def test_without_infisical_it_runs_the_command_with_platform_variables(entrypoint):
    result = entrypoint.run({"DATABASE_URL": "postgresql+asyncpg://db/app"})

    assert result.returncode == 0, result.stderr
    assert "DATABASE_URL=postgresql+asyncpg://db/app" in result.stdout
    assert "platform environment variables" in result.stderr
    assert entrypoint.calls() == []


def test_with_infisical_it_wraps_the_command_in_infisical_run(entrypoint):
    result = entrypoint.run(BOOTSTRAP)

    assert result.returncode == 0, result.stderr
    login, run = entrypoint.calls()
    assert login.startswith("login --method=universal-auth")
    assert "--domain=https://infisical.example.test" in login
    assert "--projectId=proj-123" in run
    assert "--env=staging" in run
    assert "--token=fake-token" in run
    assert "env=staging" in result.stderr


def test_the_app_never_sees_the_long_lived_client_credentials(entrypoint):
    result = entrypoint.run(BOOTSTRAP)

    assert result.returncode == 0, result.stderr
    assert "S3cretClient" not in result.stdout
    assert "INFISICAL_CLIENT_ID" not in result.stdout
    assert "S3cretClient" not in result.stderr


def test_the_app_never_sees_the_access_token(entrypoint):
    result = entrypoint.run(BOOTSTRAP)

    assert result.returncode == 0, result.stderr
    assert "INFISICAL_TOKEN" not in result.stdout
    assert "fake-token" not in result.stdout


def test_an_inherited_infisical_token_is_not_passed_to_the_app(entrypoint):
    result = entrypoint.run({**BOOTSTRAP, "INFISICAL_TOKEN": "inherited-token"})

    assert result.returncode == 0, result.stderr
    assert "INFISICAL_TOKEN" not in result.stdout
    assert "inherited-token" not in result.stdout


def test_partial_infisical_config_fails_instead_of_falling_back(entrypoint):
    env = {k: v for k, v in BOOTSTRAP.items() if k != "INFISICAL_CLIENT_SECRET"}

    result = entrypoint.run(env)

    assert result.returncode != 0
    assert "INFISICAL_CLIENT_SECRET" in result.stderr
    assert entrypoint.calls() == []


@pytest.mark.parametrize("slug", ["dev", "development", "local"])
def test_a_development_slug_is_refused(entrypoint, slug):
    result = entrypoint.run({**BOOTSTRAP, "INFISICAL_ENV": slug})

    assert result.returncode != 0
    assert f"INFISICAL_ENV={slug}" in result.stderr
    assert entrypoint.calls() == []


def test_a_development_slug_can_be_allowed_explicitly(entrypoint):
    env = {**BOOTSTRAP, "INFISICAL_ENV": "dev", "INFISICAL_ALLOW_DEV_ENV": "true"}

    result = entrypoint.run(env)

    assert result.returncode == 0, result.stderr
    assert "--env=dev" in entrypoint.calls()[1]


def test_the_universal_auth_and_domain_aliases_are_accepted(entrypoint):
    env = {
        "INFISICAL_PROJECT_ID": "proj-123",
        "INFISICAL_UNIVERSAL_AUTH_CLIENT_ID": "client-abc",
        "INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET": "S3cretClient",
        "INFISICAL_ENV": "prod",
        "INFISICAL_DOMAIN": "https://alias.example.test",
    }

    result = entrypoint.run(env)

    assert result.returncode == 0, result.stderr
    assert "S3cretClient" not in result.stdout
    assert "--domain=https://alias.example.test" in entrypoint.calls()[0]


def test_a_failed_login_stops_the_container(entrypoint):
    result = entrypoint.run({**BOOTSTRAP, "FAKE_LOGIN_FAILS": "1"})

    assert result.returncode != 0
    assert "login failed" in result.stderr
    assert len(entrypoint.calls()) == 1
