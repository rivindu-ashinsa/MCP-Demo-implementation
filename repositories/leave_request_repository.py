from db.models import LeaveRequest
from repositories.base import TenantScopedRepository


class LeaveRequestRepository(TenantScopedRepository[LeaveRequest]):
    model = LeaveRequest

    def get_for_employee(self, employee_id: int) -> list[LeaveRequest]:
        return (
            self.scoped()
            .filter(LeaveRequest.employee_id == employee_id)
            .order_by(LeaveRequest.requested_at.desc())
            .all()
        )

    def get_by_status(self, status: str) -> list[LeaveRequest]:
        return (
            self.scoped()
            .filter(LeaveRequest.status == status)
            .order_by(LeaveRequest.requested_at)
            .all()
        )

    def get_all(self) -> list[LeaveRequest]:
        return self.scoped().order_by(LeaveRequest.requested_at.desc()).all()