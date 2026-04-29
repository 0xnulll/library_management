from __future__ import annotations

import grpc
import pytest

from app.grpc_gen import auth_pb2, book_pb2, common_pb2


@pytest.mark.asyncio
async def test_login_returns_token(stubs) -> None:
    resp = await stubs["auth"].Login(
        auth_pb2.LoginRequest(username="admin", password="admin")
    )
    assert resp.token_type == "bearer"
    assert resp.access_token


@pytest.mark.asyncio
async def test_login_rejects_bad_password(stubs) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["auth"].Login(
            auth_pb2.LoginRequest(username="admin", password="nope")
        )
    assert info.value.code() == grpc.StatusCode.UNAUTHENTICATED


@pytest.mark.asyncio
async def test_protected_rpc_requires_token(stubs) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["book"].SearchBooks(book_pb2.SearchBooksRequest())
    assert info.value.code() == grpc.StatusCode.UNAUTHENTICATED


@pytest.mark.asyncio
async def test_me_returns_username(stubs, auth_metadata) -> None:
    resp = await stubs["auth"].Me(common_pb2.Empty(), metadata=auth_metadata)
    assert resp.username == "admin"


@pytest.mark.asyncio
async def test_invalid_token_rejected(stubs) -> None:
    bad_meta = (("authorization", "Bearer not-a-real-jwt"),)
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["auth"].Me(common_pb2.Empty(), metadata=bad_meta)
    assert info.value.code() == grpc.StatusCode.UNAUTHENTICATED
