from __future__ import annotations

import grpc

from app.core.config import Settings
from app.core.security import JWTEncoder, PasswordHasher
from app.grpc_app.servicers._session import SessionFactory, session_scope
from app.grpc_gen import auth_pb2, auth_pb2_grpc, common_pb2
from app.infrastructure.repositories import SqlUserRepository
from app.services.auth_service import AuthService


class AuthServicer(auth_pb2_grpc.AuthServiceServicer):
    def __init__(self, session_factory: SessionFactory, settings: Settings) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._hasher = PasswordHasher()
        self._encoder = JWTEncoder(settings)

    async def Login(  # noqa: N802 (grpc method name)
        self,
        request: auth_pb2.LoginRequest,
        context: grpc.aio.ServicerContext,
    ) -> auth_pb2.TokenResponse:
        with session_scope(self._session_factory) as session:
            service = AuthService(
                SqlUserRepository(session), self._hasher, self._encoder, self._settings
            )
            token = service.login(request.username, request.password)
        return auth_pb2.TokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
        )

    async def Me(  # noqa: N802
        self,
        request: common_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> auth_pb2.CurrentUser:
        username = _username_from_metadata(context, self._encoder)
        return auth_pb2.CurrentUser(username=username)

    async def Logout(  # noqa: N802
        self,
        request: common_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> common_pb2.Empty:
        return common_pb2.Empty()


def _username_from_metadata(
    context: grpc.aio.ServicerContext, encoder: JWTEncoder
) -> str:
    """Decode the bearer token already validated by ``JwtAuthInterceptor``.

    The interceptor only verifies the signature; ``Me`` is the one place we
    actually need the subject, so we decode again here. It's already trusted.
    """
    for entry in context.invocation_metadata() or ():
        key, value = entry.key, entry.value
        if key.lower() == "authorization" and isinstance(value, str):
            token = value.removeprefix("Bearer ").removeprefix("bearer ").strip()
            return str(encoder.decode(token).get("sub", ""))
    return ""
