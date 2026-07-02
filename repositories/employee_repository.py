from sqlalchemy import func

from db.models import Employee
from repositories.base import TenantScopedRepository


class EmployeeRepository(TenantScopedRepository[Employee]):
    model = Employee

    def get_by_local_id(self, local_id: int) -> Employee | None:
        return self.scoped().filter(Employee.local_id == local_id).first()

    def get_by_name(self, name: str) -> Employee | None:
        return self.scoped().filter(func.lower(Employee.name) == name.strip().lower()).first()

    def department_headcounts(self) -> dict[str, int]:
        rows = (
            self.scoped()
            .with_entities(Employee.department, func.count(Employee.id))
            .group_by(Employee.department)
            .order_by(Employee.department)
            .all()
        )
        return {department: count for department, count in rows}

    def next_local_id(self) -> int:
        """Next per-tenant employee id, continuing the same numbering the
        original employees.json used (1, 2, 3…) so new hires slot in
        the same way migrated ones did."""
        current_max = self.scoped().with_entities(func.max(Employee.local_id)).scalar()
        return (current_max or 0) + 1

    def update_leave_balance(self, employee: Employee, new_balance: int) -> Employee:
        employee.leave_balance = new_balance
        return employee