import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.core.config import ENV_FILES


class _TestDatabase(BaseSettings):
    # TEST_DATABASE_URL from the environment or .env. No fallback: tests never guess a DB.
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    test_database_url: str


TEST_DATABASE_URL = _TestDatabase.model_validate({}).test_database_url
if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
    raise RuntimeError("Refusing to run tests against a non-test database (name must end in _test)")

os.environ["ENV"] = "test"
os.environ["AUTH_MODE"] = "dev"
# Hard override: a dev DATABASE_URL exported by `just`/dotenv must never leak into tests.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from collections.abc import AsyncIterator, Callable  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine  # noqa: E402

from app.api.deps import get_card_generator  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.generation.fake import FakeCardGenerator  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    # Run the real Alembic migrations once per test run, so migrations are tested too.
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
async def engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(test_database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    # Each test runs inside a transaction that is rolled back at the end.
    # session.commit() inside app code only releases a SAVEPOINT.
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        await session.close()
        await trans.rollback()


@pytest.fixture
def app() -> FastAPI:
    app = create_app()
    # Never call a real LLM in tests. Individual tests can override this again.
    app.dependency_overrides[get_card_generator] = FakeCardGenerator
    return app


@pytest.fixture
def override_settings(app: FastAPI) -> Callable[..., Settings]:
    """override_settings(max_cards=2): this test's app sees changed config, nothing else does."""

    def apply(**changes: object) -> Settings:
        settings = get_settings().model_copy(update=changes)
        app.dependency_overrides[get_settings] = lambda: settings
        return settings

    return apply


@pytest.fixture
async def client(session: AsyncSession, app: FastAPI) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
