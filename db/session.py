import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.base import Base
from db import models  # noqa: F401  (import so Base.metadata sees the models)

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DB_DIR / "app.db")))

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # SQLite + FastAPI's threaded workers
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Creates tables if they don't exist yet. Safe to call on every startup."""
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: `db: Session = Depends(get_db)`."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Session:
    """For code outside a request (MCP tools, scripts): `with session_scope() as db:`.
    Commits on clean exit, rolls back on exception."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_default_accounts() -> None:
    """
    Dev/demo convenience: if the database has no companies at all yet, create
    one demo company with an HR login and one member login, so there's
    something to log in with on a fresh checkout without manually running
    db/migrate_json.py first.

    Safe to call on every startup — it's a no-op once any company exists.
    Controlled by SEED_DEFAULT_ACCOUNTS in .env (default: on).
    """
    if os.getenv("SEED_DEFAULT_ACCOUNTS", "true").lower() != "true":
        return

    # Imported here, not at module level, to avoid a circular import
    # (repositories/services import db.session; db.session must not import
    # them back at import time).
    from db.models import Company, Employee, User
    from repositories.company_repository import CompanyRepository
    from repositories.employee_repository import EmployeeRepository
    from repositories.user_repository import UserRepository
    from services.auth_service import hash_password

    with session_scope() as db:
        if db.query(Company).first() is not None:
            return  # already have real tenant data — never overwrite it

        company_code = os.getenv("SEED_COMPANY_CODE", "demo")
        company_name = os.getenv("SEED_COMPANY_NAME", "Demo Company")
        hr_username = os.getenv("SEED_HR_USERNAME", "admin")
        hr_password = os.getenv("SEED_HR_PASSWORD", "admin123")

        company_repo = CompanyRepository(db)
        company = company_repo.add(Company(name=company_name, code=company_code))
        db.flush()  # populate company.id

        user_repo = UserRepository(db, company.id)
        user_repo.add(
            User(username=hr_username, password_hash=hash_password(hr_password), role="hr", employee_id=None)
        )

        emp_repo = EmployeeRepository(db, company.id)
        demo_employee = emp_repo.add(
            Employee(local_id=1, name="Demo Employee", department="General", leave_balance=10)
        )
        db.flush()  # populate demo_employee.id

        member_username = "demo.employee"
        member_password = "1"  # matches the "seed password = employee's local id" convention
        user_repo.add(
            User(
                username=member_username,
                password_hash=hash_password(member_password),
                role="member",
                employee_id=demo_employee.id,
            )
        )

    print(
        "\nSeeded a default demo login (no company existed yet):\n"
        f"  Company code : {company_code}\n"
        f"  HR login     : {hr_username} / {hr_password}\n"
        f"  Member login : {member_username} / {member_password}\n"
        "Set SEED_DEFAULT_ACCOUNTS=false in .env once you've migrated real data.\n"
    )