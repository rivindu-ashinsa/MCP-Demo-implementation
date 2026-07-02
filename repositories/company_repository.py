from sqlalchemy.orm import Session

from db.models import Company


class CompanyRepository:
    """Company isn't tenant-scoped by anything else — it *is* the tenant."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> Company | None:
        return self.db.query(Company).filter(Company.code == code.strip().lower()).first()

    def add(self, instance: Company) -> Company:
        self.db.add(instance)
        return instance