from __future__ import annotations

from app.grpc_app.converters.time import datetime_to_proto
from app.grpc_gen import book_pb2
from app.services.book_service import BookResponse


def book_to_proto(b: BookResponse) -> book_pb2.Book:
    msg = book_pb2.Book(
        id=b.id,
        title=b.title,
        author=b.author,
        isbn=b.isbn or "",
        total_copies=b.total_copies,
        available_copies=b.available_copies,
    )
    if (created := datetime_to_proto(b.created_at)) is not None:
        msg.created_at.CopyFrom(created)
    if (updated := datetime_to_proto(b.updated_at)) is not None:
        msg.updated_at.CopyFrom(updated)
    return msg
