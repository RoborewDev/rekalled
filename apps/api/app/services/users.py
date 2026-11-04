from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_or_create_user(session: AsyncSession, provider: str, subject: str) -> User:
    """Just-in-time user creation. Safe if two first requests race."""
    _ = await session.execute(
        insert(User)
        .values(auth_provider=provider, auth_subject=subject)
        .on_conflict_do_nothing(index_elements=["auth_provider", "auth_subject"])
    )
    user = await session.scalar(
        select(User).where(User.auth_provider == provider, User.auth_subject == subject)
    )
    assert user is not None
    await session.commit()
    return user
