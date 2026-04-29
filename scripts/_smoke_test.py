"""Comprehensive smoke test:

1. Native gRPC on :50051  -> exercise every RPC, including failure paths
2. gRPC-Web on :8000      -> verify Envoy translation + CORS preflight
3. Frontend HTML on :3000 -> verify it renders the login page

Output is intended to be human-readable and short.
"""

from __future__ import annotations

import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path

import grpc

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "backend"))

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


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def expect_grpc_error(stub_call, code: grpc.StatusCode, label: str) -> None:
    try:
        stub_call()
    except grpc.RpcError as exc:
        actual = exc.code()
        if actual == code:
            ok(f"{label} -> {actual.name}: {exc.details()!r}")
            return
        raise SystemExit(f"FAIL {label}: expected {code.name}, got {actual.name}") from exc
    raise SystemExit(f"FAIL {label}: expected {code.name}, got success")


def native_grpc(target: str) -> None:
    section(f"native gRPC @ {target}")

    with grpc.insecure_channel(target) as channel:
        auth = auth_pb2_grpc.AuthServiceStub(channel)
        books = book_pb2_grpc.BookServiceStub(channel)
        members = member_pb2_grpc.MemberServiceStub(channel)
        loans = loan_pb2_grpc.LoanServiceStub(channel)

        # --- AUTH ---
        token = auth.Login(auth_pb2.LoginRequest(username="admin", password="admin")).access_token
        ok(f"Login -> token len={len(token)}")
        meta = (("authorization", f"Bearer {token}"),)

        me = auth.Me(common_pb2.Empty(), metadata=meta)
        assert me.username == "admin"
        ok(f"Me -> {me.username}")

        expect_grpc_error(
            lambda: auth.Login(auth_pb2.LoginRequest(username="admin", password="wrong")),
            grpc.StatusCode.UNAUTHENTICATED,
            "Login(bad password)",
        )
        expect_grpc_error(
            lambda: books.SearchBooks(book_pb2.SearchBooksRequest()),
            grpc.StatusCode.UNAUTHENTICATED,
            "SearchBooks(no token)",
        )

        # --- BOOKS ---
        b1 = books.CreateBook(
            book_pb2.CreateBookRequest(title="Dune", author="Frank Herbert",
                                        isbn="9780441172719", total_copies=2),
            metadata=meta,
        )
        ok(f"CreateBook -> id={b1.id} avail={b1.available_copies}/{b1.total_copies}")

        b2 = books.CreateBook(
            book_pb2.CreateBookRequest(title="1984", author="Orwell",
                                        isbn="9780451524935", total_copies=1),
            metadata=meta,
        )
        ok(f"CreateBook(2) -> id={b2.id}")

        got = books.GetBook(book_pb2.GetBookRequest(id=b1.id), metadata=meta)
        assert got.title == "Dune"
        ok(f"GetBook -> {got.title} by {got.author}")

        searched = books.SearchBooks(
            book_pb2.SearchBooksRequest(query="dune",
                                         pagination=common_pb2.Pagination(limit=10)),
            metadata=meta,
        )
        assert any(b.id == b1.id for b in searched.books)
        ok(f"SearchBooks('dune') -> {len(searched.books)} hit(s)")

        updated = books.UpdateBook(
            book_pb2.UpdateBookRequest(id=b1.id, title="Dune (revised)",
                                        author="Frank Herbert", isbn=b1.isbn,
                                        total_copies=3),
            metadata=meta,
        )
        assert updated.total_copies == 3
        ok(f"UpdateBook -> total_copies={updated.total_copies}")

        expect_grpc_error(
            lambda: books.GetBook(book_pb2.GetBookRequest(id=99999), metadata=meta),
            grpc.StatusCode.NOT_FOUND,
            "GetBook(missing)",
        )
        expect_grpc_error(
            lambda: books.CreateBook(
                book_pb2.CreateBookRequest(title="", author="x", isbn="", total_copies=1),
                metadata=meta,
            ),
            grpc.StatusCode.INVALID_ARGUMENT,
            "CreateBook(empty title)",
        )

        # --- MEMBERS ---
        m1 = members.CreateMember(
            member_pb2.CreateMemberRequest(full_name="Alice Reader",
                                             email="alice@example.com", phone="555-0100"),
            metadata=meta,
        )
        ok(f"CreateMember -> id={m1.id}")

        m2 = members.CreateMember(
            member_pb2.CreateMemberRequest(full_name="Bob Reader",
                                             email="bob@example.com", phone=""),
            metadata=meta,
        )
        ok(f"CreateMember(2) -> id={m2.id}")

        listing = members.ListMembers(
            member_pb2.ListMembersRequest(pagination=common_pb2.Pagination(limit=50)),
            metadata=meta,
        )
        assert len(listing.members) >= 2
        ok(f"ListMembers -> {len(listing.members)}")

        expect_grpc_error(
            lambda: members.CreateMember(
                member_pb2.CreateMemberRequest(full_name="dup",
                                                 email="alice@example.com", phone=""),
                metadata=meta,
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
            "CreateMember(duplicate email)",
        )
        expect_grpc_error(
            lambda: members.CreateMember(
                member_pb2.CreateMemberRequest(full_name="bad", email="not-an-email", phone=""),
                metadata=meta,
            ),
            grpc.StatusCode.INVALID_ARGUMENT,
            "CreateMember(invalid email)",
        )

        # --- LOANS ---
        loan1 = loans.Borrow(
            loan_pb2.BorrowRequest(book_id=b2.id, member_id=m1.id),
            metadata=meta,
        )
        ok(f"Borrow(b2, alice) -> loan id={loan1.id}")

        post = books.GetBook(book_pb2.GetBookRequest(id=b2.id), metadata=meta)
        assert post.available_copies == 0
        ok(f"GetBook(b2) -> available {post.available_copies}/{post.total_copies}")

        expect_grpc_error(
            lambda: loans.Borrow(
                loan_pb2.BorrowRequest(book_id=b2.id, member_id=m2.id), metadata=meta
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
            "Borrow(b2 again -> no copies)",
        )
        expect_grpc_error(
            lambda: loans.Borrow(
                loan_pb2.BorrowRequest(book_id=b2.id, member_id=m1.id), metadata=meta
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
            "Borrow(b2 same member twice)",
        )

        loan2 = loans.Borrow(
            loan_pb2.BorrowRequest(book_id=b1.id, member_id=m2.id),
            metadata=meta,
        )
        ok(f"Borrow(b1, bob) -> loan id={loan2.id}")

        active_alice = loans.ListLoansByMember(
            loan_pb2.ListLoansByMemberRequest(member_id=m1.id), metadata=meta
        )
        assert len(active_alice.loans) == 1
        ok(f"ListLoansByMember(alice) -> {len(active_alice.loans)}")

        all_active = loans.ListLoans(
            loan_pb2.ListLoansRequest(active_only=True,
                                       pagination=common_pb2.Pagination(limit=50)),
            metadata=meta,
        )
        assert len(all_active.loans) == 2
        ok(f"ListLoans(active_only) -> {len(all_active.loans)}")

        returned = loans.ReturnLoan(
            loan_pb2.ReturnLoanRequest(loan_id=loan1.id), metadata=meta
        )
        assert returned.HasField("returned_at")
        ok("ReturnLoan(loan1) -> ok")

        expect_grpc_error(
            lambda: loans.ReturnLoan(
                loan_pb2.ReturnLoanRequest(loan_id=loan1.id), metadata=meta
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
            "ReturnLoan(twice)",
        )

        post = books.GetBook(book_pb2.GetBookRequest(id=b2.id), metadata=meta)
        assert post.available_copies == 1
        ok(f"GetBook(b2) after return -> available {post.available_copies}/{post.total_copies}")

        # back to a clean slate-ish: alice can re-borrow b2 now
        again = loans.Borrow(
            loan_pb2.BorrowRequest(book_id=b2.id, member_id=m1.id), metadata=meta
        )
        ok(f"Borrow(b2 again after return) -> loan id={again.id}")

        # finally, logout (server-stateless ack)
        auth.Logout(common_pb2.Empty(), metadata=meta)
        ok("Logout -> ok")


def grpc_web_via_envoy(base: str) -> None:
    section(f"gRPC-Web @ {base}")

    # CORS preflight
    req = urllib.request.Request(
        f"{base}/library.auth.AuthService/Login",
        method="OPTIONS",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-grpc-web,authorization",
        },
    )
    resp = urllib.request.urlopen(req, timeout=5)
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    ok(f"CORS preflight -> {resp.status} ACAO={resp.headers['access-control-allow-origin']}")

    # Real Login over gRPC-Web framing
    body = auth_pb2.LoginRequest(username="admin", password="admin").SerializeToString()
    frame = b"\x00" + struct.pack(">I", len(body)) + body

    req = urllib.request.Request(
        f"{base}/library.auth.AuthService/Login",
        data=frame,
        method="POST",
        headers={
            "Content-Type": "application/grpc-web+proto",
            "X-Grpc-Web": "1",
            "Origin": "http://localhost:3000",
        },
    )
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read()
    flag, length = struct.unpack(">BI", data[:5])
    payload = data[5:5 + length]
    token_resp = auth_pb2.TokenResponse()
    token_resp.ParseFromString(payload)
    assert token_resp.access_token, "no access_token in gRPC-Web response"
    ok(f"Login over gRPC-Web -> {resp.status} token len={len(token_resp.access_token)}")


def frontend(base: str) -> None:
    section(f"frontend @ {base}")

    for path, must_contain in [
        ("/login", "Sign in"),
        ("/", None),
    ]:
        try:
            resp = urllib.request.urlopen(f"{base}{path}", timeout=10)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"FAIL frontend {path}: HTTP {exc.code}") from exc
        body = resp.read().decode("utf-8", errors="ignore")
        if must_contain and must_contain not in body:
            raise SystemExit(f"FAIL frontend {path}: did not find {must_contain!r}")
        ok(f"GET {path} -> {resp.status} ({len(body)} bytes)")


def main() -> int:
    native_grpc("127.0.0.1:50051")
    grpc_web_via_envoy("http://127.0.0.1:8000")
    frontend("http://127.0.0.1:3000")
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
