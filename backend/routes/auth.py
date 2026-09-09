from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.session import SessionLocal
from models.user_model import User
from models.user import UserSchema


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# --------------------------------------------------
# Login Request
# --------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


# --------------------------------------------------
# Register
# --------------------------------------------------

@router.post("/register")
def register(user: UserSchema):

    db = SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(User.email == user.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered."
            )

        new_user = User(
            name=user.name,
            email=user.email,
            password=user.password,
            role=user.role
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User Registered Successfully",
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role
            }
        }

    finally:
        db.close()


# --------------------------------------------------
# Login
# --------------------------------------------------

@router.post("/login")
def login(data: LoginRequest):

    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(
                User.email == data.email,
                User.password == data.password
            )
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid Email or Password."
            )

        return {
            "message": "Login Successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }

    finally:
        db.close()