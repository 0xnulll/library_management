"""Denormalize active loan count onto books table

Stores the running count of unreturned loans on each book row, so that read
paths (search, get, list) no longer need to JOIN/COUNT against the loans table.
The column is maintained transactionally by LoanService on borrow / return.

Revision ID: 0002_book_active_loan_count
Revises: 0001_initial
Create Date: 2026-04-30
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_book_active_loan_count"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) add nullable column first so we can backfill, then make it NOT NULL.
    op.add_column(
        "books",
        sa.Column(
            "active_loan_count",
            sa.Integer(),
            nullable=True,
            server_default="0",
        ),
    )

    # 2) lock down the column: NOT NULL + non-negative invariant
    op.alter_column("books", "active_loan_count", nullable=False)
    op.create_check_constraint(
        "ck_books_active_loan_count_nonneg",
        "books",
        "active_loan_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_books_active_loan_count_nonneg", "books", type_="check"
    )
    op.drop_column("books", "active_loan_count")
