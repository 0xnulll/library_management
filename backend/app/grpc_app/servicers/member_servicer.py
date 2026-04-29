from __future__ import annotations

import grpc

from app.grpc_app.converters import member_to_proto
from app.grpc_app.dto import CreateMemberDTO, UpdateMemberDTO
from app.grpc_app.dto._parse import parse_or_invalid
from app.grpc_app.servicers._session import SessionFactory, session_scope
from app.grpc_gen import member_pb2, member_pb2_grpc
from app.infrastructure.repositories import SqlMemberRepository
from app.services.member_service import MemberService


class MemberServicer(member_pb2_grpc.MemberServiceServicer):
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def _service(self, session) -> MemberService:
        return MemberService(SqlMemberRepository(session))

    async def CreateMember(  # noqa: N802
        self,
        request: member_pb2.CreateMemberRequest,
        context: grpc.aio.ServicerContext,
    ) -> member_pb2.Member:
        dto = parse_or_invalid(CreateMemberDTO.from_proto, req=request)
        with session_scope(self._session_factory) as session:
            member = self._service(session).create(
                full_name=dto.full_name,
                email=dto.email,
                phone=dto.phone,
            )
        return member_to_proto(member)

    async def UpdateMember(  # noqa: N802
        self,
        request: member_pb2.UpdateMemberRequest,
        context: grpc.aio.ServicerContext,
    ) -> member_pb2.Member:
        dto = parse_or_invalid(UpdateMemberDTO.from_proto, req=request)
        with session_scope(self._session_factory) as session:
            member = self._service(session).update(
                dto.id,
                full_name=dto.full_name,
                email=dto.email,
                phone=dto.phone,
            )
        return member_to_proto(member)

    async def GetMember(  # noqa: N802
        self,
        request: member_pb2.GetMemberRequest,
        context: grpc.aio.ServicerContext,
    ) -> member_pb2.Member:
        with session_scope(self._session_factory) as session:
            member = self._service(session).get(request.id)
        return member_to_proto(member)

    async def ListMembers(  # noqa: N802
        self,
        request: member_pb2.ListMembersRequest,
        context: grpc.aio.ServicerContext,
    ) -> member_pb2.ListMembersResponse:
        limit = request.pagination.limit or 50
        offset = request.pagination.offset or 0
        with session_scope(self._session_factory) as session:
            members = self._service(session).list(limit, offset)
        return member_pb2.ListMembersResponse(members=[member_to_proto(m) for m in members])
