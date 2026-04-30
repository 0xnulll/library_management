from __future__ import annotations

import grpc

from app.grpc_app.converters import book_to_proto
from app.grpc_app.dto import CreateBookDTO, UpdateBookDTO
from app.grpc_app.dto._parse import parse_or_invalid
from app.grpc_app.servicers._session import SessionFactory, session_scope
from app.grpc_gen import book_pb2, book_pb2_grpc
from app.infrastructure.repositories import SqlBookRepository
from app.services.book_service import BookService


class BookServicer(book_pb2_grpc.BookServiceServicer):
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def _service(self, session) -> BookService:
        return BookService(SqlBookRepository(session))

    async def CreateBook(  # noqa: N802
        self,
        request: book_pb2.CreateBookRequest,
        context: grpc.aio.ServicerContext,
    ) -> book_pb2.Book:
        dto = parse_or_invalid(CreateBookDTO.from_proto, req=request)
        with session_scope(self._session_factory) as session:
            book = self._service(session).create(
                title=dto.title,
                author=dto.author,
                isbn=dto.isbn,
                total_copies=dto.total_copies,
            )
        return book_to_proto(book)

    async def UpdateBook(  # noqa: N802
        self,
        request: book_pb2.UpdateBookRequest,
        context: grpc.aio.ServicerContext,
    ) -> book_pb2.Book:
        dto = parse_or_invalid(UpdateBookDTO.from_proto, req=request)
        with session_scope(self._session_factory) as session:
            book = self._service(session).update(
                dto.id,
                title=dto.title,
                author=dto.author,
                isbn=dto.isbn,
                total_copies=dto.total_copies,
            )
        return book_to_proto(book)

    async def GetBook(  # noqa: N802
        self,
        request: book_pb2.GetBookRequest,
        context: grpc.aio.ServicerContext,
    ) -> book_pb2.Book:
        with session_scope(self._session_factory) as session:
            book = self._service(session).get(request.id)
        return book_to_proto(book)

    async def SearchBooks(  # noqa: N802
        self,
        request: book_pb2.SearchBooksRequest,
        context: grpc.aio.ServicerContext,
    ) -> book_pb2.SearchBooksResponse:
        limit = request.pagination.limit or 50
        offset = request.pagination.offset or 0
        with session_scope(self._session_factory) as session:
            books = self._service(session).search(request.query or None, limit, offset)
        return book_pb2.SearchBooksResponse(books=[book_to_proto(b) for b in books])
