"""Minimal gRPC client that exercises the library API end-to-end.

Run against ``backend:50051`` (or any address) once ``docker compose up`` is
running. Requires ``grpcio`` and the generated stubs from ``app.grpc_gen``.

Usage:
    python scripts/sample_client.py --target 127.0.0.1:50051
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import grpc

# Make ``app.grpc_gen`` importable when running from a checkout without
# installing the backend.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend"))
sys.path.insert(0, str(_REPO_ROOT / "backend/app/grpc_gen"))

from app.grpc_gen import (  # noqa: E402
    auth_pb2,
    auth_pb2_grpc,
    book_pb2,
    book_pb2_grpc,
    common_pb2,
    loan_pb2,
    loan_pb2_grpc,
    member_pb2,
    member_pb2_grpc,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="127.0.0.1:50051")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args()

    with grpc.insecure_channel(args.target) as channel:
        auth = auth_pb2_grpc.AuthServiceStub(channel)
        token = auth.Login(
            auth_pb2.LoginRequest(username=args.user, password=args.password)
        ).access_token
        print("logged in")
        meta = (("authorization", f"Bearer {token}"),)

        books = book_pb2_grpc.BookServiceStub(channel)
        members = member_pb2_grpc.MemberServiceStub(channel)
        loans = loan_pb2_grpc.LoanServiceStub(channel)

        book = books.CreateBook(
            book_pb2.CreateBookRequest(
                title="The Pragmatic Programmer",
                author="Hunt & Thomas",
                isbn="9780135957059",
                total_copies=1,
            ),
            metadata=meta,
        )
        print(f"created book: {book.id} {book.title}")

        member = members.CreateMember(
            member_pb2.CreateMemberRequest(
                full_name="Sample Reader", email="reader@example.com", phone=""
            ),
            metadata=meta,
        )
        print(f"created member: {member.id} {member.full_name}")

        loan = loans.Borrow(
            loan_pb2.BorrowRequest(book_id=book.id, member_id=member.id),
            metadata=meta,
        )
        print(f"borrowed loan: {loan.id} due {loan.due_at.ToJsonString()}")

        active = loans.ListLoansByMember(
            loan_pb2.ListLoansByMemberRequest(member_id=member.id), metadata=meta
        )
        print(f"active loans for member: {len(active.loans)}")

        returned = loans.ReturnLoan(
            loan_pb2.ReturnLoanRequest(loan_id=loan.id), metadata=meta
        )
        print(f"returned at: {returned.returned_at.ToJsonString()}")

        empty = common_pb2.Empty()
        me = auth.Me(empty, metadata=meta)
        print(f"current user: {me.username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
