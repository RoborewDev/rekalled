"""The real token path, with EC P-384 keys generated here instead of Logto's JWKS."""

import base64
import hashlib
import hmac
import json
import logging
import time
from collections.abc import Callable, Mapping
from typing import cast

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import AsyncClient
from jwt.algorithms import ECAlgorithm

from app.auth.dependencies import get_token_verifier
from app.auth.logto import InvalidTokenError, JwksKeyResolver, LogtoTokenVerifier
from app.core.config import Settings, get_settings

ISSUER = "https://tenant.logto.app/oidc"
AUDIENCE = "https://api.rekalled.app"
CLIENT_ID = "spa-app-id"
SIGNING_KEY = ec.generate_private_key(ec.SECP384R1())
OTHER_KEY = ec.generate_private_key(ec.SECP384R1())


class StaticKeys:
    def key_for(self, token: str) -> ec.EllipticCurvePublicKey:
        kid = jwt.get_unverified_header(token).get("kid")
        if kid != "test-key":
            raise jwt.PyJWKClientError(f"Unknown kid {kid}")
        return SIGNING_KEY.public_key()


def token(
    *,
    key: ec.EllipticCurvePrivateKey = SIGNING_KEY,
    kid: str = "test-key",
    typ: str = "at+jwt",
    scope: str = "decks:read decks:write cards:generate",
    **overrides: object,
) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "logto-user-1",
        "client_id": CLIENT_ID,
        "scope": scope,
        "iat": now,
        "exp": now + 3600,
    } | overrides
    return jwt.encode(claims, key, algorithm="ES384", headers={"kid": kid, "typ": typ})


def unsigned_claims() -> dict[str, object]:
    claims: dict[str, object] = jwt.decode(token(), options={"verify_signature": False})
    return claims


def raw_token(
    header: Mapping[str, object], claims: Mapping[str, object], sign: Callable[[bytes], bytes]
) -> str:
    """Build a JWT by hand, for algorithms PyJWT refuses to produce on purpose."""

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    signing_input = f"{b64(json.dumps(header).encode())}.{b64(json.dumps(claims).encode())}"
    return f"{signing_input}.{b64(sign(signing_input.encode()))}"


def hs384_with_public_key() -> str:
    # The classic algorithm-confusion attack: HMAC "signed" with the public key.
    public_pem = SIGNING_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    header = {"alg": "HS384", "typ": "at+jwt", "kid": "test-key"}
    return raw_token(
        header, unsigned_claims(), lambda m: hmac.new(public_pem, m, hashlib.sha384).digest()
    )


def alg_none() -> str:
    return raw_token(
        {"alg": "none", "typ": "at+jwt", "kid": "test-key"}, unsigned_claims(), lambda m: b""
    )


def without_exp() -> str:
    claims = unsigned_claims()
    del claims["exp"]
    return jwt.encode(
        claims, SIGNING_KEY, algorithm="ES384", headers={"kid": "test-key", "typ": "at+jwt"}
    )


def bearer(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


def jwks(*keys: tuple[str, ec.EllipticCurvePublicKey]) -> dict[str, object]:
    """A JWKS response shaped like the tenant's, for a mocked PyJWKClient."""
    return {
        "keys": [
            {**ECAlgorithm.to_jwk(public_key, as_dict=True), "kid": kid} for kid, public_key in keys
        ]
    }


def verifier_from_settings(endpoint: str) -> LogtoTokenVerifier:
    """Build the verifier the way the app does, from Settings rather than an override."""
    verifier = get_token_verifier(
        Settings.model_validate(
            {
                "_env_file": None,
                "env": "test",
                "auth_mode": "logto",
                "card_generator": "fake",
                "logto_endpoint": endpoint,
                "logto_api_resource": AUDIENCE,
                "logto_app_id": CLIENT_ID,
            }
        )
    )
    assert verifier is not None
    return verifier


@pytest.fixture(autouse=True)
def logto_mode(app: FastAPI) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {
            "_env_file": None,
            "env": "test",
            "auth_mode": "logto",
            "logto_endpoint": "https://tenant.logto.app",
            "logto_api_resource": AUDIENCE,
            "logto_app_id": CLIENT_ID,
        }
    )
    app.dependency_overrides[get_token_verifier] = lambda: LogtoTokenVerifier(
        issuer=ISSUER, audience=AUDIENCE, client_id=CLIENT_ID, keys=StaticKeys()
    )


async def test_a_valid_token_identifies_the_user(client: AsyncClient) -> None:
    response = await client.get("/v1/me", headers=bearer(token()))

    assert response.status_code == 200
    assert response.json()["scopes"] == ["cards:generate", "decks:read", "decks:write"]


async def test_the_same_subject_is_the_same_user(client: AsyncClient) -> None:
    first = cast("dict[str, object]", (await client.get("/v1/me", headers=bearer(token()))).json())
    second = cast("dict[str, object]", (await client.get("/v1/me", headers=bearer(token()))).json())

    assert first["id"] == second["id"]


async def test_missing_token_is_401(client: AsyncClient) -> None:
    response = await client.get("/v1/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "bad_token",
    [
        pytest.param(lambda: token(exp=int(time.time()) - 10), id="expired"),
        pytest.param(lambda: token(iss="https://evil.example/oidc"), id="wrong issuer"),
        pytest.param(lambda: token(aud="https://other-api"), id="wrong audience"),
        pytest.param(lambda: token(key=OTHER_KEY), id="tampered signature"),
        pytest.param(lambda: token(kid="rotated-away"), id="unknown kid"),
        pytest.param(lambda: token(typ="JWT"), id="id token, not access token"),
        pytest.param(lambda: token(client_id="another-app"), id="wrong client"),
        pytest.param(hs384_with_public_key, id="HS384 signed with the public key"),
        pytest.param(alg_none, id="alg none"),
        pytest.param(without_exp, id="no exp"),
    ],
)
async def test_invalid_tokens_are_401(client: AsyncClient, bad_token: Callable[[], str]) -> None:
    response = await client.get("/v1/me", headers=bearer(bad_token()))

    assert response.status_code == 401


async def test_a_missing_scope_is_403(client: AsyncClient) -> None:
    read_only = token(scope="decks:read")

    assert (await client.get("/v1/decks", headers=bearer(read_only))).status_code == 200
    response = await client.post("/v1/decks", json={"name": "x"}, headers=bearer(read_only))
    assert response.status_code == 403


async def test_dev_header_is_ignored_in_logto_mode(client: AsyncClient) -> None:
    response = await client.get("/v1/me", headers={"X-Dev-User": "dev|local"})

    assert response.status_code == 401


def test_the_real_resolver_fetches_the_settings_jwks_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetches: list[str] = []

    def fetch_data(self: jwt.PyJWKClient) -> dict[str, object]:
        fetches.append(self.uri)
        return jwks(("test-key", SIGNING_KEY.public_key()))

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fetch_data)
    verifier = verifier_from_settings("https://resolver.logto.app")
    signed = token(iss="https://resolver.logto.app/oidc")

    first = verifier.verify(signed)
    second = verifier.verify(signed)

    assert fetches == ["https://resolver.logto.app/oidc/jwks"]
    assert first == second
    assert first.subject == "logto-user-1"
    assert first.scopes == frozenset({"decks:read", "decks:write", "cards:generate"})


def blocked_jwks(_self: jwt.PyJWKClient, _token: str | bytes) -> jwt.PyJWK:
    # What a WAF in front of Logto looks like to PyJWT: the JWKS fetch itself fails.
    raise jwt.PyJWKClientConnectionError(
        'Fail to fetch data from the url, err: "HTTP Error 403: Forbidden"'
    )


async def test_unreachable_signing_keys_are_503_not_401(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jwt.PyJWKClient, "get_signing_key_from_jwt", blocked_jwks)
    app.dependency_overrides[get_token_verifier] = lambda: LogtoTokenVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        client_id=CLIENT_ID,
        keys=JwksKeyResolver("https://tenant.logto.app/oidc/jwks"),
    )

    response = await client.get("/v1/me", headers=bearer(token()))

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service unavailable"


async def test_a_rejected_token_logs_why_without_the_token(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    rejected = token(client_id="another-app")

    with caplog.at_level(logging.WARNING, logger="app.auth.dependencies"):
        response = await client.get("/v1/me", headers=bearer(rejected))

    assert response.status_code == 401
    assert "Token was issued to a different client" in caplog.text
    assert rejected not in caplog.text


def test_the_jwks_client_sends_an_explicit_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    real_client = jwt.PyJWKClient
    captured: dict[str, object] = {}

    def fake_client(uri: str, **kwargs: object):
        captured.update(kwargs)
        return real_client(uri, cache_keys=True, timeout=5)

    monkeypatch.setattr(jwt, "PyJWKClient", fake_client)

    _ = JwksKeyResolver("https://tenant.logto.app/oidc/jwks")

    assert captured["headers"] == {"User-Agent": "rekalled-api"}


def test_a_token_without_a_kid_is_rejected_by_the_real_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fetch_data(_self: jwt.PyJWKClient) -> dict[str, object]:
        return jwks(("test-key", SIGNING_KEY.public_key()))

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fetch_data)
    verifier = verifier_from_settings("https://no-kid.logto.app")
    claims = unsigned_claims() | {"iss": "https://no-kid.logto.app/oidc"}
    without_kid = jwt.encode(claims, SIGNING_KEY, algorithm="ES384", headers={"typ": "at+jwt"})

    with pytest.raises(InvalidTokenError):
        _ = verifier.verify(without_kid)
