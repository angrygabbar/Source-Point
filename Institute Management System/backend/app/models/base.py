import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    Time,
    false,
    func,
    true,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ----------------------------------------------------------------------------- column helpers


def pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def fk(target: str, nullable: bool = True, ondelete: str = "RESTRICT", index: bool = True, **info: Any):
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
        index=index,
        info=info,
    )


def uuid_col(nullable: bool = True, **info: Any):
    return mapped_column(UUID(as_uuid=True), nullable=nullable, info=info)


def string(length: int = 255, nullable: bool = True, default: str | None = None, index: bool = False, **info: Any):
    return mapped_column(
        String(length),
        nullable=nullable,
        default=default,
        server_default=default if default is not None else None,
        index=index,
        info=info,
    )


def text(nullable: bool = True, **info: Any):
    return mapped_column(Text, nullable=nullable, info=info)


def money(nullable: bool = False, default: Decimal | None = Decimal("0.00"), **info: Any):
    return mapped_column(
        Numeric(12, 2),
        nullable=nullable,
        default=default,
        server_default=str(default) if default is not None else None,
        info={"widget": "money", **info},
    )


def decimal(precision: int = 10, scale: int = 2, nullable: bool = True, default: Decimal | None = None, **info: Any):
    return mapped_column(
        Numeric(precision, scale),
        nullable=nullable,
        default=default,
        server_default=str(default) if default is not None else None,
        info=info,
    )


def enum(*values: str, default: str | None = None, nullable: bool = False, **info: Any):
    return mapped_column(
        SAEnum(*values, native_enum=False, create_constraint=True, length=40, validate_strings=True),
        nullable=nullable,
        default=default,
        server_default=default,
        index=False,
        info=info,
    )


def boolean(default: bool = False, **info: Any):
    return mapped_column(Boolean, nullable=False, default=default, server_default=true() if default else false(), info=info)


def integer(nullable: bool = True, default: int | None = None, **info: Any):
    return mapped_column(
        Integer, nullable=nullable, default=default, server_default=str(default) if default is not None else None, info=info
    )


def bigint(nullable: bool = True, default: int | None = None, **info: Any):
    return mapped_column(
        BigInteger, nullable=nullable, default=default, server_default=str(default) if default is not None else None, info=info
    )


def date(nullable: bool = True, index: bool = False, **info: Any):
    return mapped_column(Date, nullable=nullable, index=index, info=info)


def ts(nullable: bool = True, index: bool = False, **info: Any):
    return mapped_column(DateTime(timezone=True), nullable=nullable, index=index, info=info)


def time(nullable: bool = True, **info: Any):
    return mapped_column(Time, nullable=nullable, info=info)


def jsonb(default: str = "object", **info: Any):
    if default == "list":
        return mapped_column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"), info=info)
    return mapped_column(JSONB, nullable=False, default=dict, server_default=sql_text("'{}'::jsonb"), info=info)


# ----------------------------------------------------------------------------- mixins


class IdMixin:
    id = pk()


class TimestampMixin:
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TenantMixin:
    @declared_attr
    def institute_id(cls):
        return mapped_column(UUID(as_uuid=True), ForeignKey("institutes.id", ondelete="RESTRICT"), nullable=False, index=True)


class BranchMixin:
    @declared_attr
    def branch_id(cls):
        return mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)


class OptionalBranchMixin:
    @declared_attr
    def branch_id(cls):
        return mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True)


class ActorMixin:
    @declared_attr
    def created_by_id(cls):
        return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def updated_by_id(cls):
        return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ArchiveMixin:
    is_archived = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    archived_at = mapped_column(DateTime(timezone=True), nullable=True)


class Entity(IdMixin, TimestampMixin):
    pass


class TenantEntity(IdMixin, TimestampMixin, TenantMixin):
    pass


class BranchEntity(IdMixin, TimestampMixin, TenantMixin, BranchMixin):
    pass


class OptBranchEntity(IdMixin, TimestampMixin, TenantMixin, OptionalBranchMixin):
    pass
