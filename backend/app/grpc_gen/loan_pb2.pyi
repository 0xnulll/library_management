import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Loan(_message.Message):
    __slots__ = ("id", "book_id", "member_id", "borrowed_at", "due_at", "returned_at", "is_overdue")
    ID_FIELD_NUMBER: _ClassVar[int]
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    MEMBER_ID_FIELD_NUMBER: _ClassVar[int]
    BORROWED_AT_FIELD_NUMBER: _ClassVar[int]
    DUE_AT_FIELD_NUMBER: _ClassVar[int]
    RETURNED_AT_FIELD_NUMBER: _ClassVar[int]
    IS_OVERDUE_FIELD_NUMBER: _ClassVar[int]
    id: int
    book_id: int
    member_id: int
    borrowed_at: _timestamp_pb2.Timestamp
    due_at: _timestamp_pb2.Timestamp
    returned_at: _timestamp_pb2.Timestamp
    is_overdue: bool
    def __init__(self, id: _Optional[int] = ..., book_id: _Optional[int] = ..., member_id: _Optional[int] = ..., borrowed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., due_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., returned_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., is_overdue: bool = ...) -> None: ...

class BorrowRequest(_message.Message):
    __slots__ = ("book_id", "member_id", "days")
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    MEMBER_ID_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    book_id: int
    member_id: int
    days: int
    def __init__(self, book_id: _Optional[int] = ..., member_id: _Optional[int] = ..., days: _Optional[int] = ...) -> None: ...

class ReturnLoanRequest(_message.Message):
    __slots__ = ("loan_id",)
    LOAN_ID_FIELD_NUMBER: _ClassVar[int]
    loan_id: int
    def __init__(self, loan_id: _Optional[int] = ...) -> None: ...

class ListLoansRequest(_message.Message):
    __slots__ = ("member_id", "book_id", "active_only", "pagination")
    MEMBER_ID_FIELD_NUMBER: _ClassVar[int]
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ONLY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    member_id: int
    book_id: int
    active_only: bool
    pagination: _common_pb2.Pagination
    def __init__(self, member_id: _Optional[int] = ..., book_id: _Optional[int] = ..., active_only: bool = ..., pagination: _Optional[_Union[_common_pb2.Pagination, _Mapping]] = ...) -> None: ...

class ListLoansByMemberRequest(_message.Message):
    __slots__ = ("member_id",)
    MEMBER_ID_FIELD_NUMBER: _ClassVar[int]
    member_id: int
    def __init__(self, member_id: _Optional[int] = ...) -> None: ...

class ListLoansResponse(_message.Message):
    __slots__ = ("loans",)
    LOANS_FIELD_NUMBER: _ClassVar[int]
    loans: _containers.RepeatedCompositeFieldContainer[Loan]
    def __init__(self, loans: _Optional[_Iterable[_Union[Loan, _Mapping]]] = ...) -> None: ...
