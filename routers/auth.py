from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Company, User
from repositories.company_repository import CompanyRepository
from repositories.user_repository import UserRepository
from services.auth_service import create_access_token, verify_password, hash_password
from routers.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    company_code: str
    username: str
    password: str


class RegisterRequest(BaseModel):
    company_code: str
    username: str
    password: str


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    company_repo = CompanyRepository(db)

    if company_repo.get_by_code(request.company_code) is not None:
        raise HTTPException(status_code=400, detail="Company code is already taken.")

    # No separate company_name in the request, so the code doubles as the
    # display name for now — adjust here if Company requires a distinct name.
    company = company_repo.add(Company(code=request.company_code, name=request.company_code))
    db.flush()  # populate company.id before creating the user below

    user_repo = UserRepository(db, company.id)
    if user_repo.get_by_username(request.username) is not None:
        raise HTTPException(status_code=400, detail="Username is already taken.")

    user = user_repo.add(
        User(
            username=request.username,
            password_hash=hash_password(request.password),
            role="hr",          # first user of a new company is its HR admin
            employee_id=None,
        )
    )
    db.flush()
    db.commit()

    token = create_access_token(
        company_id=company.id,
        company_name=company.name,
        username=user.username,
        role=user.role,
        employee_id=user.employee_id,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "company_name": company.name,
        "employee_id": user.employee_id,
    }


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)) -> dict:
    company = CompanyRepository(db).get_by_code(request.company_code)
    if company is None:
        raise HTTPException(status_code=401, detail="Unknown company code.")

    user = UserRepository(db, company.id).get_by_username(request.username)
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    token = create_access_token(
        company_id=company.id,
        company_name=company.name,
        username=user.username,
        role=user.role,
        employee_id=user.employee_id,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "company_name": company.name,
        "employee_id": user.employee_id,
    }


@router.get("/me")
def whoami(user: dict = Depends(get_current_user)) -> dict:
    return {
        "username": user["username"],
        "role": user["role"],
        "company_name": user["company_name"],
        "employee_id": user.get("employee_id"),
    }