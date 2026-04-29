from __future__ import annotations

from app.grpc_app.converters.time import datetime_to_proto
from app.grpc_gen import loan_pb2
from app.services.response_type import LoanResponse


def loan_to_proto(loan: LoanResponse) -> loan_pb2.Loan:
    msg = loan_pb2.Loan(
        id=loan.id,
        book_id=loan.book_id,
        member_id=loan.member_id,
        is_overdue=loan.is_overdue,
    )
    if (borrowed := datetime_to_proto(loan.borrowed_at)) is not None:
        msg.borrowed_at.CopyFrom(borrowed)
    if (due := datetime_to_proto(loan.due_at)) is not None:
        msg.due_at.CopyFrom(due)
    if (returned := datetime_to_proto(loan.returned_at)) is not None:
        msg.returned_at.CopyFrom(returned)
    return msg
