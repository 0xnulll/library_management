from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import grpc
from grpc.aio import ServerInterceptor

from app.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


_STATUS_MAP: dict[type[DomainError], grpc.StatusCode] = {
    NotFoundError: grpc.StatusCode.NOT_FOUND,
    ConflictError: grpc.StatusCode.FAILED_PRECONDITION,
    AuthenticationError: grpc.StatusCode.UNAUTHENTICATED,
    ValidationError: grpc.StatusCode.INVALID_ARGUMENT,
}


class ErrorMappingInterceptor(ServerInterceptor):
    """Translate domain exceptions raised by servicers into gRPC status codes."""

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = await continuation(handler_call_details)
        if handler is None or handler.unary_unary is None:
            return handler

        original = handler.unary_unary

        async def _wrapped(request: Any, context: grpc.aio.ServicerContext) -> Any:
            try:
                return await original(request, context)
            except DomainError as exc:
                code = _STATUS_MAP.get(type(exc), grpc.StatusCode.UNKNOWN)
                await context.abort(code, str(exc))
            except BaseException as exc:
                # ``context.abort`` raises ``AbortError`` (a BaseException) to unwind
                # the RPC; let it propagate untouched. Anything else is unexpected.
                if exc.__class__.__name__ == "AbortError":
                    raise
                logger.exception("unhandled error in %s", handler_call_details.method)
                await context.abort(grpc.StatusCode.INTERNAL, "internal error")

        return grpc.unary_unary_rpc_method_handler(
            _wrapped,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
