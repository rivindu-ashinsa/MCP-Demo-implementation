from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)  # short login code, e.g. "acme"
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    employees = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("company_id", "local_id", name="uq_employee_company_local_id"),)

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    local_id = Column(Integer, nullable=False)  # per-tenant id, mirrors the legacy employees.json id
    name = Column(String, nullable=False)
    department = Column(String)
    leave_balance = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    company = relationship("Company", back_populates="employees")
    user = relationship("User", back_populates="employee", uselist=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("company_id", "username", name="uq_user_company_username"),
        CheckConstraint("role IN ('hr', 'member')", name="ck_user_role"),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'hr' | 'member'
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    company = relationship("Company", back_populates="users")
    employee = relationship("Employee", back_populates="user")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_leave_status"),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)  # computed at request time, inclusive of both dates
    reason = Column(String, nullable=True)

    status = Column(String, nullable=False, default="pending")  # 'pending' | 'approved' | 'rejected'
    requested_at = Column(DateTime, default=_utcnow, nullable=False)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String, nullable=True)  # username of the HR account that decided it

    company = relationship("Company")
    employee = relationship("Employee")