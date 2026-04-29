from __future__ import annotations

from app.grpc_app.converters.time import datetime_to_proto
from app.grpc_gen import member_pb2
from app.services.response_type import MemberResponse


def member_to_proto(m: MemberResponse) -> member_pb2.Member:
    msg = member_pb2.Member(
        id=m.id,
        full_name=m.full_name,
        email=m.email,
        phone=m.phone or "",
    )
    if (created := datetime_to_proto(m.created_at)) is not None:
        msg.created_at.CopyFrom(created)
    if (updated := datetime_to_proto(m.updated_at)) is not None:
        msg.updated_at.CopyFrom(updated)
    return msg
