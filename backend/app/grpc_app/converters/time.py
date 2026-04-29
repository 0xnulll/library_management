from __future__ import annotations

from datetime import UTC, datetime

from google.protobuf.timestamp_pb2 import Timestamp


def datetime_to_proto(value: datetime | None) -> Timestamp | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    ts = Timestamp()
    ts.FromDatetime(value.astimezone(UTC))
    return ts


def proto_to_datetime(ts: Timestamp | None) -> datetime | None:
    if ts is None or (ts.seconds == 0 and ts.nanos == 0):
        return None
    return ts.ToDatetime(tzinfo=UTC)
