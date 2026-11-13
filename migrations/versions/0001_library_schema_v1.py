"""library schema v1

Revision ID: 0001_library_schema_v1
Revises:
Create Date: 2026-11-13 15:10:00+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_library_schema_v1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Maple Street Library Schema v1 tables, constraints, and indexes."""
    op.create_table(
        "books",
        sa.Column("isbn", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "isbn ~ '^([0-9]{9}[0-9X]|[0-9]{13})$'",
            name=op.f("ck_books_isbn_format"),
        ),
        sa.CheckConstraint(
            "btrim(title) <> '' AND char_length(title) <= 300",
            name=op.f("ck_books_title_valid"),
        ),
        sa.PrimaryKeyConstraint("isbn", name=op.f("pk_books")),
    )

    op.create_table(
        "members",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(name) <> '' AND char_length(name) <= 200",
            name=op.f("ck_members_name_valid"),
        ),
        sa.CheckConstraint(
            "phone IS NULL OR (char_length(phone) <= 20 AND phone ~ '^\\+?[0-9]{7,19}$')",
            name=op.f("ck_members_phone_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended')",
            name=op.f("ck_members_status_enum"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
    )

    op.create_table(
        "book_authors",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("book_isbn", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position BETWEEN 1 AND 20",
            name=op.f("ck_book_authors_position"),
        ),
        sa.CheckConstraint(
            "btrim(name) <> '' AND char_length(name) <= 200",
            name=op.f("ck_book_authors_name_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["book_isbn"],
            ["books.isbn"],
            name=op.f("fk_book_authors_book_isbn"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_book_authors")),
        sa.UniqueConstraint(
            "book_isbn",
            "name",
            name=op.f("uq_book_authors_book_isbn_name"),
        ),
        sa.UniqueConstraint(
            "book_isbn",
            "position",
            name=op.f("uq_book_authors_book_isbn_position"),
        ),
    )
    op.create_index(
        op.f("ix_book_authors_book_isbn"),
        "book_authors",
        ["book_isbn"],
        unique=False,
    )

    op.create_table(
        "copies",
        sa.Column("barcode", sa.Text(), nullable=False),
        sa.Column("book_isbn", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'available'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(barcode) <> '' AND char_length(barcode) <= 64",
            name=op.f("ck_copies_barcode_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('available', 'on_loan', 'withdrawn')",
            name=op.f("ck_copies_status_enum"),
        ),
        sa.ForeignKeyConstraint(
            ["book_isbn"],
            ["books.isbn"],
            name=op.f("fk_copies_book_isbn"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("barcode", name=op.f("pk_copies")),
    )
    op.create_index(
        op.f("ix_copies_book_isbn"),
        "copies",
        ["book_isbn"],
        unique=False,
    )

    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("copy_barcode", sa.Text(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column(
            "borrowed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "due_at > borrowed_at",
            name=op.f("ck_loans_due_after_borrow"),
        ),
        sa.CheckConstraint(
            "returned_at IS NULL OR returned_at >= borrowed_at",
            name=op.f("ck_loans_return_after_borrow"),
        ),
        sa.ForeignKeyConstraint(
            ["copy_barcode"],
            ["copies.barcode"],
            name=op.f("fk_loans_copy_barcode"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_loans_member_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loans")),
    )
    op.create_index(
        op.f("ix_loans_copy_barcode"),
        "loans",
        ["copy_barcode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_loans_member_id"),
        "loans",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        "ix_loans_member_open",
        "loans",
        ["member_id"],
        unique=False,
        postgresql_where=sa.text("returned_at IS NULL"),
    )
    op.create_index(
        "uq_loans_one_open_per_copy",
        "loans",
        ["copy_barcode"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )

    op.create_table(
        "fines",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("amount_kobo", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_kobo BETWEEN 1 AND 2000",
            name=op.f("ck_fines_amount_kobo_range"),
        ),
        sa.ForeignKeyConstraint(
            ["loan_id"],
            ["loans.id"],
            name=op.f("fk_fines_loan_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fines")),
        sa.UniqueConstraint("loan_id", name=op.f("uq_fines_loan_id")),
    )

    op.create_table(
        "fine_payments",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("fine_id", sa.Integer(), nullable=False),
        sa.Column("amount_kobo", sa.Integer(), nullable=False),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_kobo BETWEEN 1 AND 2000",
            name=op.f("ck_fine_payments_amount_kobo_range"),
        ),
        sa.ForeignKeyConstraint(
            ["fine_id"],
            ["fines.id"],
            name=op.f("fk_fine_payments_fine_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fine_payments")),
    )
    op.create_index(
        op.f("ix_fine_payments_fine_id"),
        "fine_payments",
        ["fine_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Maple Street Library Schema v1 tables, constraints, and indexes."""
    op.drop_index(op.f("ix_fine_payments_fine_id"), table_name="fine_payments")
    op.drop_table("fine_payments")

    op.drop_table("fines")

    op.drop_index(
        "uq_loans_one_open_per_copy",
        table_name="loans",
        postgresql_where=sa.text("returned_at IS NULL"),
    )
    op.drop_index(
        "ix_loans_member_open",
        table_name="loans",
        postgresql_where=sa.text("returned_at IS NULL"),
    )
    op.drop_index(op.f("ix_loans_member_id"), table_name="loans")
    op.drop_index(op.f("ix_loans_copy_barcode"), table_name="loans")
    op.drop_table("loans")

    op.drop_index(op.f("ix_copies_book_isbn"), table_name="copies")
    op.drop_table("copies")

    op.drop_index(op.f("ix_book_authors_book_isbn"), table_name="book_authors")
    op.drop_table("book_authors")

    op.drop_table("members")
    op.drop_table("books")
