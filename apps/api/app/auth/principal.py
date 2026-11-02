from dataclasses import dataclass

ALL_SCOPES = frozenset({"decks:read", "decks:write", "cards:generate"})


@dataclass(frozen=True)
class Principal:
    """Who is calling, as proven by the identity provider (or the dev bypass)."""

    provider: str
    subject: str
    scopes: frozenset[str]
