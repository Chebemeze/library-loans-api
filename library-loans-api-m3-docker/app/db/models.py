from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Book(Base):
    """One book title/edition in the catalogue, identified by unhyphenated ISBN-10/13."""

    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint(
            "isbn ~ '^([0-9]{9}[0-9X]|[0-9]{13})$'",
            name="isbn_format",
        ),
        CheckConstraint(
            "btrim(title) <> '' AND char_length(title) <= 300",
            name="title_valid",
        ),
    )

    isbn: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    authors: Mapped[list[BookAuthor]] = relationship(
        back_populates="book",
        order_by="BookAuthor.position",
        passive_deletes=True,
    )
    copies: Mapped[list[Copy]] = relationship(
        back_populates="book",
        passive_deletes=True,
    )


class BookAuthor(Base):
    """One ordered author entry (position 1..20) belonging to a book."""

    __tablename__ = "book_authors"
    __table_args__ = (
        UniqueConstraint("book_isbn", "position"),
        UniqueConstraint("book_isbn", "name"),
        CheckConstraint("position BETWEEN 1 AND 20", name="position"),
        CheckConstraint(
            "btrim(name) <> '' AND char_length(name) <= 200",
            name="name_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    book_isbn: Mapped[str] = mapped_column(
        Text,
        ForeignKey("books.isbn", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    book: Mapped[Book] = relationship(back_populates="authors")


class Copy(Base):
    """One physical copy of a book, identified by barcode."""

    __tablename__ = "copies"
    __table_args__ = (
        CheckConstraint(
            "btrim(barcode) <> '' AND char_length(barcode) <= 64",
            name="barcode_valid",
        ),
        CheckConstraint(
            "status IN ('available', 'on_loan', 'withdrawn')",
            name="status_enum",
        ),
    )

    barcode: Mapped[str] = mapped_column(Text, primary_key=True)
    book_isbn: Mapped[str] = mapped_column(
        Text,
        ForeignKey("books.isbn", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="available",
        server_default=text("'available'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    book: Mapped[Book] = relationship(back_populates="copies")
    loans: Mapped[list[Loan]] = relationship(
        back_populates="copy",
        passive_deletes=True,
    )


class Member(Base):
    """One registered library borrower, identified by public UUID."""

    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> '' AND char_length(name) <= 200",
            name="name_valid",
        ),
        CheckConstraint(
            "phone IS NULL OR (char_length(phone) <= 20 AND phone ~ '^\\+?[0-9]{7,19}$')",
            name="phone_valid",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended')",
            name="status_enum",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    loans: Mapped[list[Loan]] = relationship(
        back_populates="member",
        passive_deletes=True,
    )


class Loan(Base):
    """One borrowing event of one copy by one member."""

    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("due_at > borrowed_at", name="due_after_borrow"),
        CheckConstraint(
            "returned_at IS NULL OR returned_at >= borrowed_at",
            name="return_after_borrow",
        ),
        Index(
            "uq_loans_one_open_per_copy",
            "copy_barcode",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
        ),
        Index(
            "ix_loans_member_open",
            "member_id",
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    copy_barcode: Mapped[str] = mapped_column(
        Text,
        ForeignKey("copies.barcode", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    copy: Mapped[Copy] = relationship(back_populates="loans")
    member: Mapped[Member] = relationship(back_populates="loans")
    fine: Mapped[Fine | None] = relationship(
        back_populates="loan",
        passive_deletes=True,
    )


class Fine(Base):
    """One late-return fine on one closed loan (created only when amount_kobo > 0)."""

    __tablename__ = "fines"
    __table_args__ = (CheckConstraint("amount_kobo BETWEEN 1 AND 2000", name="amount_kobo_range"),)

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    loan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    amount_kobo: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    loan: Mapped[Loan] = relationship(back_populates="fine")
    payments: Mapped[list[FinePayment]] = relationship(
        back_populates="fine",
        order_by="FinePayment.id",
        passive_deletes=True,
    )


class FinePayment(Base):
    """One immutable positive payment against a fine (paid_kobo is SUMmed from here)."""

    __tablename__ = "fine_payments"
    __table_args__ = (CheckConstraint("amount_kobo BETWEEN 1 AND 2000", name="amount_kobo_range"),)

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    fine_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fines.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_kobo: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fine: Mapped[Fine] = relationship(back_populates="payments")
