from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from repositories.company_repository import CompanyRepository
from repositories.user_repository import UserRepository
from services.auth_service import create_access_token, verify_password
from routers.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    company_code: str
    username: str
    password: str


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