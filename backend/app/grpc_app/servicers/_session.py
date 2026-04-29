"""Helpers shared by all servicers.

A servicer is constructed with a ``SessionFactory`` callable. Every RPC opens
a fresh SQLAlchemy session, builds the application service against that
session, and commits/rolls back at the end. This keeps services free of any
gRPC awareness while still letting us scope work per request.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

SessionFactory = Callable[[], Session]


@contextmanager
def session_scope(factory: SessionFactory) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
