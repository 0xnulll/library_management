from __future__ import annotations

import grpc

from app.core.config import Settings
from app.grpc_app.converters import loan_to_proto
from app.grpc_app.dto import BorrowDTO, ReturnLoanDTO
from app.grpc_app.dto._parse import parse_or_invalid
from app.grpc_app.servicers._session import SessionFactory, session_scope
from app.grpc_gen import loan_pb2, loan_pb2_grpc
from app.infrastructure.repositories import (
    SqlBookRepository,
    SqlLoanRepository,
    SqlMemberRepository,
)
from app.services.clock import SystemClock
from app.services.loan_service import LoanService


class LoanServicer(loan_pb2_grpc.LoanServiceServicer):
    def __init__(self, session_factory: SessionFactory, settings: Settings) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._clock = SystemClock()

    def _service(self, session) -> LoanService:
        return LoanService(
            SqlBookRepository(session),
            SqlMemberRepository(session),
            SqlLoanRepository(session),
            self._clock,
            self._settings,
        )

    async def Borrow(  # noqa: N802
        self,
        request: loan_pb2.BorrowRequest,
        context: grpc.aio.ServicerContext,
    ) -> loan_pb2.Loan:
        dto = parse_or_invalid(BorrowDTO.from_proto, req=request)
        with session_scope(self._session_factory) as session:
            loan = self._service(session).borrow(
                book_id=dto.book_id,
                member_id=dto.member_id,
                days=dto.days,
            )
        return loan_to_proto(loan)

    async def ReturnLoan(  # noqa: N802
        self,
        request: loan_pb2.ReturnLoanRequest,
        context: grpc.aio.ServicerContext,
    ) -> loan_pb2.Loan:
        dto = parse_or_invalid(ReturnLoanDTO.from_proto, req=request)
        with session_scope(self._session_factory) as session:
            loan = self._service(session).return_book(dto.loan_id)
        return loan_to_proto(loan)

    async def ListLoans(  # noqa: N802
        self,
        request: loan_pb2.ListLoansRequest,
        context: grpc.aio.ServicerContext,
    ) -> loan_pb2.ListLoansResponse:
        limit = request.pagination.limit or 50
        offset = request.pagination.offset or 0
        with session_scope(self._session_factory) as session:
            loans = self._service(session).list(
                member_id=request.member_id or None,
                book_id=request.book_id or None,
                active_only=request.active_only,
                limit=limit,
                offset=offset,
            )
        return loan_pb2.ListLoansResponse(loans=[loan_to_proto(loan) for loan in loans])

    async def ListLoansByMember(  # noqa: N802
        self,
        request: loan_pb2.ListLoansByMemberRequest,
        context: grpc.aio.ServicerContext,
    ) -> loan_pb2.ListLoansResponse:
        with session_scope(self._session_factory) as session:
            loans = self._service(session).list_for_member(request.member_id)
        return loan_pb2.ListLoansResponse(loans=[loan_to_proto(loan) for loan in loans])
