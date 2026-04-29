from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import grpc
import jwt
from grpc.aio import ServerInterceptor

from app.core.security import JWTEncoder

logger = logging.getLogger(__name__)

AUTH_USER_KEY = "library.username"

# Methods that do not require authentication.
_PUBLIC_METHODS: frozenset[str] = frozenset(
    {
        "/library.auth.AuthService/Login",
        "/grpc.health.v1.Health/Check",
        "/grpc.reflection.v1.ServerReflection/ServerReflectionInfo",
        "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
    }
)


class JwtAuthInterceptor(ServerInterceptor):
    """Validate ``authorization: Bearer <token>`` metadata on every RPC.

    Login (and reflection/health) bypass the check. The decoded subject is
    placed on the invocation context so servicers can look up ``current user``
    via ``context.invocation_metadata`` without re-validating the token.
    """

    def __init__(self, encoder: JWTEncoder) -> None:
        self._encoder = encoder

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        method = handler_call_details.method
        if method in _PUBLIC_METHODS:
            return await continuation(handler_call_details)

        token = _extract_bearer(handler_call_details.invocation_metadata)
        if token is None:
            return _abort_handler(grpc.StatusCode.UNAUTHENTICATED, "missing token")
        try:
            claims = self._encoder.decode(token)
        except jwt.PyJWTError:
            return _abort_handler(grpc.StatusCode.UNAUTHENTICATED, "invalid token")

        sub = claims.get("sub")
        if not isinstance(sub, str):
            return _abort_handler(grpc.StatusCode.UNAUTHENTICATED, "invalid token subject")

        return await continuation(handler_call_details)


def _extract_bearer(metadata: tuple[Any, ...] | None) -> str | None:
    if not metadata:
        return None
    for entry in metadata:
        key = getattr(entry, "key", None)
        value = getattr(entry, "value", None)
        if key is None and isinstance(entry, tuple) and len(entry) == 2:
            key, value = entry
        if (
            key
            and key.lower() == "authorization"
            and isinstance(value, str)
            and value.lower().startswith("bearer ")
        ):
            return value[7:].strip()
    return None


def _abort_handler(code: grpc.StatusCode, detail: str) -> grpc.RpcMethodHandler:
    async def _abort(_request: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(code, detail)

    return grpc.unary_unary_rpc_method_handler(_abort)
