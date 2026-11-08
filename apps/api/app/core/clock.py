from datetime import UTC, datetime


def get_now() -> datetime:
    """Injected as a dependency so tests can control time."""
    return datetime.now(UTC)
