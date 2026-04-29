from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Iterator

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(current_dir, "app")
grpc_gen_dir = os.path.join(app_dir, "grpc_gen")
sys.path.insert(0, app_dir)
sys.path.insert(0, grpc_gen_dir)


import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool, StaticPool  # noqa: E402

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")

import grpc  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.security import PasswordHasher  # noqa: E402
from app.domain.entities import StaffUser  # noqa: E402
from app.grpc_app.server import build_server  # noqa: E402
from app.grpc_gen import (  # noqa: E402
    auth_pb2_grpc,
    book_pb2_grpc,
    loan_pb2_grpc,
    member_pb2_grpc,
)
from app.infrastructure.db.base import Base  # noqa: E402
from app.infrastructure.db.session import Database  # noqa: E402
from app.infrastructure.repositories import SqlUserRepository  # noqa: E402


class _SqliteDatabase(Database):
    """SQLite database used for component tests.

    Two flavours:
      * in-memory + ``StaticPool`` for fast single-threaded tests;
      * file-backed + ``NullPool`` so each thread gets its own connection
        and we can exercise real concurrent borrow behaviour.
    """

    def __init__(self, path: str | None = None) -> None:
        if path is None:
            self._engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                future=True,
            )
        else:
            self._engine = create_engine(
                f"sqlite:///{path}",
                connect_args={"check_same_thread": False, "timeout": 5},
                poolclass=NullPool,
                future=True,
            )

        @event.listens_for(self._engine, "connect")
        def _on_connect(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.isolation_level = None
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

        @event.listens_for(self._engine, "begin")
        def _begin_immediate(conn):  # noqa: ANN001
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(
            bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False
        )


@pytest.fixture()
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture()
def db(request, tmp_path) -> Iterator[_SqliteDatabase]:
    marker = request.node.get_closest_marker("file_db")
    if marker is not None:
        database = _SqliteDatabase(path=str(tmp_path / "library.db"))
    else:
        database = _SqliteDatabase()
    yield database
    database.engine.dispose()


@pytest.fixture()
def admin_user(db: _SqliteDatabase) -> StaffUser:
    session: Session = db.session()
    try:
        repo = SqlUserRepository(session)
        hasher = PasswordHasher()
        user = repo.add(
            StaffUser(
                id=None,
                username="admin",
                password_hash=hasher.hash("admin"),
                is_active=True,
            )
        )
        session.commit()
        return user
    finally:
        session.close()


@pytest_asyncio.fixture()
async def grpc_server(
    db: _SqliteDatabase, settings: Settings, admin_user: StaffUser
) -> AsyncIterator[str]:
    server = build_server(settings, db.session, enable_reflection=False)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await server.stop(grace=None)


@pytest_asyncio.fixture()
async def channel(grpc_server: str) -> AsyncIterator[grpc.aio.Channel]:
    async with grpc.aio.insecure_channel(grpc_server) as channel:
        yield channel


@pytest_asyncio.fixture()
async def auth_metadata(channel: grpc.aio.Channel) -> tuple[tuple[str, str], ...]:
    from app.grpc_gen import auth_pb2

    stub = auth_pb2_grpc.AuthServiceStub(channel)
    resp = await stub.Login(auth_pb2.LoginRequest(username="admin", password="admin"))
    return (("authorization", f"Bearer {resp.access_token}"),)


@pytest.fixture()
def stubs(channel: grpc.aio.Channel) -> dict[str, object]:
    return {
        "auth": auth_pb2_grpc.AuthServiceStub(channel),
        "book": book_pb2_grpc.BookServiceStub(channel),
        "member": member_pb2_grpc.MemberServiceStub(channel),
        "loan": loan_pb2_grpc.LoanServiceStub(channel),
    }
