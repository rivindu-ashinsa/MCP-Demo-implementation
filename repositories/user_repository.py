from db.models import User
from repositories.base import TenantScopedRepository


class UserRepository(TenantScopedRepository[User]):
    model = User

    def get_by_username(self, username: str) -> User | None:
        return self.scoped().filter(User.username == username.strip()).first()

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None