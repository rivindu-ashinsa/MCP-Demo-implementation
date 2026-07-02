"""
Base tenant-scoped repository.

Every subclass gets company_id baked in at construction time.
self.scoped() is the only entry point to the DB — there is no method
on this class that can return another tenant's rows.
"""
from typing import Generic, Type, TypeVar
from sqlalchemy.orm import Session, Query


ModelT = TypeVar("ModelT")


class TenantScopedRepository(Generic[ModelT]):
    model: Type[ModelT]  # set by each subclass

    def __init__(self, db: Session, company_id: int) -> None:
        self.db = db
        self.company_id = company_id

    # ── Core scoped query ────────────────────────────────────────────────

    def scoped(self) -> Query:
        """
        Returns a Query pre-filtered to this tenant.
        Every other method MUST build on this — never use
        self.db.query(self.model) directly inside a subclass.
        """
        return self.db.query(self.model).filter(
            self.model.company_id == self.company_id
        )

    # ── Generic CRUD helpers ─────────────────────────────────────────────

    def get_all(self) -> list[ModelT]:
        return self.scoped().all()

    def get_by_pk(self, pk_column, pk_value) -> ModelT | None:
        return self.scoped().filter(pk_column == pk_value).first()

    def add(self, instance: ModelT) -> ModelT:
        """
        Stamp company_id on the instance before adding, so callers never
        have to remember to set it themselves.
        """
        instance.company_id = self.company_id
        self.db.add(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        self.db.delete(instance)