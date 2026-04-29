from __future__ import annotations

import logging
from collections.abc import Callable

import grpc
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import JWTEncoder, PasswordHasher
from app.grpc_app.interceptors import ErrorMappingInterceptor, JwtAuthInterceptor
from app.grpc_app.servicers import (
    AuthServicer,
    BookServicer,
    LoanServicer,
    MemberServicer,
)
from app.grpc_gen import (
    auth_pb2_grpc,
    book_pb2_grpc,
    loan_pb2_grpc,
    member_pb2_grpc,
)
from app.infrastructure.db.session import Database
from app.infrastructure.repositories import SqlUserRepository
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


SessionFactory = Callable[[], Session]


def build_server(
    settings: Settings,
    session_factory: SessionFactory,
    *,
    enable_reflection: bool = True,
) -> grpc.aio.Server:
    """Build a gRPC asyncio server with all servicers and interceptors wired."""
    server = grpc.aio.server(
        interceptors=[
            ErrorMappingInterceptor(),
            JwtAuthInterceptor(JWTEncoder(settings)),
        ]
    )

    auth_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthServicer(session_factory, settings), server
    )
    book_pb2_grpc.add_BookServiceServicer_to_server(
        BookServicer(session_factory), server
    )
    member_pb2_grpc.add_MemberServiceServicer_to_server(
        MemberServicer(session_factory), server
    )
    loan_pb2_grpc.add_LoanServiceServicer_to_server(
        LoanServicer(session_factory, settings), server
    )

    return server


def seed_admin(db: Database, settings: Settings, username: str, password: str) -> None:
    session = db.session()
    try:
        AuthService(
            SqlUserRepository(session),
            PasswordHasher(),
            JWTEncoder(settings),
            settings,
        ).ensure_seed_user(username, password)
        session.commit()
    except Exception:
        session.rollback()
        logger.warning("seed admin failed; continuing", exc_info=True)
    finally:
        session.close()
