from __future__ import annotations

import grpc
import pytest

from app.grpc_gen import book_pb2, common_pb2, loan_pb2, member_pb2


@pytest.mark.asyncio
async def test_create_search_book(stubs, auth_metadata) -> None:
    book = await stubs["book"].CreateBook(
        book_pb2.CreateBookRequest(
            title="Dune", author="Frank Herbert", isbn="9780441172719", total_copies=2
        ),
        metadata=auth_metadata,
    )
    assert book.id > 0
    assert book.available_copies == 2

    listing = await stubs["book"].SearchBooks(
        book_pb2.SearchBooksRequest(query="dune", pagination=common_pb2.Pagination(limit=10)),
        metadata=auth_metadata,
    )
    assert any(b.id == book.id for b in listing.books)


@pytest.mark.asyncio
async def test_update_book_validates_total_copies(stubs, auth_metadata) -> None:
    book = await stubs["book"].CreateBook(
        book_pb2.CreateBookRequest(
            title="Foundation", author="Asimov", isbn="", total_copies=1
        ),
        metadata=auth_metadata,
    )
    member = await stubs["member"].CreateMember(
        member_pb2.CreateMemberRequest(full_name="Jane Doe", email="jane@example.com", phone=""),
        metadata=auth_metadata,
    )
    await stubs["loan"].Borrow(
        loan_pb2.BorrowRequest(book_id=book.id, member_id=member.id),
        metadata=auth_metadata,
    )

    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["book"].UpdateBook(
            book_pb2.UpdateBookRequest(
                id=book.id, title="Foundation", author="Asimov", isbn="", total_copies=0
            ),
            metadata=auth_metadata,
        )
    assert info.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_member_email_uniqueness(stubs, auth_metadata) -> None:
    req = member_pb2.CreateMemberRequest(full_name="Alice", email="alice@example.com", phone="")
    await stubs["member"].CreateMember(req, metadata=auth_metadata)
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["member"].CreateMember(req, metadata=auth_metadata)
    assert info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_invalid_email_rejected(stubs, auth_metadata) -> None:
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["member"].CreateMember(
            member_pb2.CreateMemberRequest(full_name="Bob", email="not-an-email", phone=""),
            metadata=auth_metadata,
        )
    assert info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
