from __future__ import annotations

import threading

import grpc
import pytest

from app.core.config import get_settings
from app.domain.entities import Book, Member
from app.domain.exceptions import ConflictError
from app.grpc_gen import book_pb2, loan_pb2, member_pb2
from app.infrastructure.repositories import (
    SqlBookRepository,
    SqlLoanRepository,
    SqlMemberRepository,
)
from app.services.clock import SystemClock
from app.services.loan_service import LoanService


@pytest.fixture()
async def book_id(stubs, auth_metadata) -> int:
    resp = await stubs["book"].CreateBook(
        book_pb2.CreateBookRequest(
            title="1984", author="Orwell", isbn="9780451524935", total_copies=1
        ),
        metadata=auth_metadata,
    )
    return resp.id


@pytest.fixture()
async def member_id(stubs, auth_metadata) -> int:
    resp = await stubs["member"].CreateMember(
        member_pb2.CreateMemberRequest(full_name="Bob", email="bob@example.com", phone="555-0100"),
        metadata=auth_metadata,
    )
    return resp.id


@pytest.fixture()
async def second_member_id(stubs, auth_metadata) -> int:
    resp = await stubs["member"].CreateMember(
        member_pb2.CreateMemberRequest(full_name="Carol", email="carol@example.com", phone=""),
        metadata=auth_metadata,
    )
    return resp.id


@pytest.mark.asyncio
async def test_borrow_then_return(stubs, auth_metadata, book_id, member_id) -> None:
    loan = await stubs["loan"].Borrow(
        loan_pb2.BorrowRequest(book_id=book_id, member_id=member_id),
        metadata=auth_metadata,
    )
    assert loan.id > 0
    assert not loan.HasField("returned_at")

    book = await stubs["book"].GetBook(book_pb2.GetBookRequest(id=book_id), metadata=auth_metadata)
    assert book.available_copies == 0

    returned = await stubs["loan"].ReturnLoan(
        loan_pb2.ReturnLoanRequest(loan_id=loan.id), metadata=auth_metadata
    )
    assert returned.HasField("returned_at")

    book = await stubs["book"].GetBook(book_pb2.GetBookRequest(id=book_id), metadata=auth_metadata)
    assert book.available_copies == 1


@pytest.mark.asyncio
async def test_cannot_double_borrow_single_copy(
    stubs, auth_metadata, book_id, member_id, second_member_id
) -> None:
    await stubs["loan"].Borrow(
        loan_pb2.BorrowRequest(book_id=book_id, member_id=member_id),
        metadata=auth_metadata,
    )
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["loan"].Borrow(
            loan_pb2.BorrowRequest(book_id=book_id, member_id=second_member_id),
            metadata=auth_metadata,
        )
    assert info.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    assert "available" in info.value.details()


@pytest.mark.asyncio
async def test_cannot_borrow_twice_same_member(stubs, auth_metadata, member_id) -> None:
    book = await stubs["book"].CreateBook(
        book_pb2.CreateBookRequest(
            title="Brave New World", author="Huxley", isbn="", total_copies=5
        ),
        metadata=auth_metadata,
    )
    await stubs["loan"].Borrow(
        loan_pb2.BorrowRequest(book_id=book.id, member_id=member_id),
        metadata=auth_metadata,
    )
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["loan"].Borrow(
            loan_pb2.BorrowRequest(book_id=book.id, member_id=member_id),
            metadata=auth_metadata,
        )
    assert info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_cannot_return_twice(stubs, auth_metadata, book_id, member_id) -> None:
    loan = await stubs["loan"].Borrow(
        loan_pb2.BorrowRequest(book_id=book_id, member_id=member_id),
        metadata=auth_metadata,
    )
    await stubs["loan"].ReturnLoan(
        loan_pb2.ReturnLoanRequest(loan_id=loan.id), metadata=auth_metadata
    )
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await stubs["loan"].ReturnLoan(
            loan_pb2.ReturnLoanRequest(loan_id=loan.id), metadata=auth_metadata
        )
    assert info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_list_loans_for_member(stubs, auth_metadata, book_id, member_id) -> None:
    await stubs["loan"].Borrow(
        loan_pb2.BorrowRequest(book_id=book_id, member_id=member_id),
        metadata=auth_metadata,
    )
    resp = await stubs["loan"].ListLoansByMember(
        loan_pb2.ListLoansByMemberRequest(member_id=member_id), metadata=auth_metadata
    )
    assert len(resp.loans) == 1
    assert resp.loans[0].book_id == book_id


@pytest.mark.file_db
def test_concurrent_borrow_only_one_succeeds(db, admin_user) -> None:  # noqa: ARG001
    """Two threads race to borrow the only copy. Exactly one must win.

    This is a service-level test that bypasses gRPC; the locking guarantee lives
    in ``LoanService.borrow`` and we want to assert it without async/event-loop
    plumbing. The transport-level conflict is covered by the test above.
    """
    settings = get_settings()
    session = db.session()
    try:
        book = SqlBookRepository(session).add(
            Book(id=None, title="Race", author="X", isbn=None, total_copies=1)
        )
        member1 = SqlMemberRepository(session).add(
            Member(id=None, full_name="A", email="a@example.com", phone=None)
        )
        member2 = SqlMemberRepository(session).add(
            Member(id=None, full_name="B", email="b@example.com", phone=None)
        )
        session.commit()
    finally:
        session.close()

    book_id_value = book.id
    assert book_id_value is not None
    results: list[tuple[str, str]] = []
    barrier = threading.Barrier(2)

    def attempt(member: int) -> None:
        barrier.wait()
        s = db.session()
        try:
            service = LoanService(
                SqlBookRepository(s),
                SqlMemberRepository(s),
                SqlLoanRepository(s),
                SystemClock(),
                settings,
            )
            service.borrow(book_id=book_id_value, member_id=member)
            s.commit()
            results.append(("ok", str(member)))
        except ConflictError as exc:
            s.rollback()
            results.append(("conflict", str(exc)))
        except Exception as exc:
            s.rollback()
            results.append(("error", type(exc).__name__))
        finally:
            s.close()

    t1 = threading.Thread(target=attempt, args=(member1.id,))
    t2 = threading.Thread(target=attempt, args=(member2.id,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [r for r in results if r[0] == "ok"]
    assert len(successes) == 1, results

    s = db.session()
    try:
        active = SqlLoanRepository(s).count_active_for_book(book_id_value)
    finally:
        s.close()
    assert active == 1
