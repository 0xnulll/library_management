from datetime import UTC, datetime, timedelta

from app.domain.entities import Loan


def test_active_when_not_returned() -> None:
    now = datetime.now(tz=UTC)
    loan = Loan(
        id=1, book_id=1, member_id=1, borrowed_at=now, due_at=now + timedelta(days=14),
        returned_at=None,
    )
    assert loan.is_active is True
    assert loan.is_overdue(now + timedelta(days=1)) is False
    assert loan.is_overdue(now + timedelta(days=15)) is True


def test_inactive_after_return() -> None:
    now = datetime.now(tz=UTC)
    loan = Loan(
        id=1, book_id=1, member_id=1, borrowed_at=now, due_at=now + timedelta(days=14),
        returned_at=now + timedelta(days=2),
    )
    assert loan.is_active is False
    assert loan.is_overdue(now + timedelta(days=20)) is False
