"""Validates Logto access tokens. The only backend code that knows about Logto."""

from typing import Protocol, cast

import jwt
from jwt.algorithms import AllowedPublicKeys

from app.auth.principal import Principal

ALGORITHMS = ["ES384"]  # Logto's default signing key type. Check your tenant's JWKS.


class InvalidTokenError(Exception):
    pass


class KeyResolver(Protocol):
    def key_for(self, token: str) -> AllowedPublicKeys: ...


class JwksKeyResolver:
    """Fetches and caches the tenant's public keys from its JWKS endpoint."""

    def __init__(self, jwks_url: str) -> None:
        # 5 s, not PyJWT's 30 s: a slow JWKS endpoint must not hang requests for long.
        self._client: jwt.PyJWKClient = jwt.PyJWKClient(jwks_url, cache_keys=True, timeout=5)

    def key_for(self, token: str) -> AllowedPublicKeys:
        # PyJWK.key is untyped in PyJWT, but from_jwk() only returns cryptography key objects.
        return cast(AllowedPublicKeys, self._client.get_signing_key_from_jwt(token).key)


class LogtoTokenVerifier:
    def __init__(self, *, issuer: str, audience: str, client_id: str, keys: KeyResolver) -> None:
        self._issuer: str = issuer
        self._audience: str = audience
        self._client_id: str = client_id
        self._keys: KeyResolver = keys

    def verify(self, token: str) -> Principal:
        try:
            # Access tokens are typed at+jwt. This stops an ID token being used as one.
            if jwt.get_unverified_header(token).get("typ") != "at+jwt":
                raise InvalidTokenError("Not an access token")
            claims: dict[str, object] = jwt.decode(
                token,
                self._keys.key_for(token),
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (jwt.PyJWTError, KeyError) as exc:
            raise InvalidTokenError(str(exc)) from exc

        # Unconditional: a security boundary must not depend on a guard in Settings.
        if claims.get("client_id") != self._client_id:
            raise InvalidTokenError("Token was issued to a different client")
        sub = claims["sub"]
        scope = claims.get("scope", "")
        if not isinstance(sub, str) or not isinstance(scope, str):
            raise InvalidTokenError("Token subject and scope must be strings")
        return Principal(
            provider="logto",
            subject=sub,
            scopes=frozenset(scope.split()),
        )
