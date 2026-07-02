import re

from repositories.user_repository import UserRepository


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", name.strip().lower()).strip(".")
    return slug or "user"


def unique_username(user_repo: UserRepository, base: str) -> str:
    candidate = base
    n = 1
    while user_repo.username_exists(candidate):
        n += 1
        candidate = f"{base}{n}"
    return candidate