from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.session import SessionLocal
from models.user_model import User


router = APIRouter(
    prefix="/users",
    tags=["User Management"]
)


# --------------------------------------------------
# Request model for creating/updating a user
# --------------------------------------------------

class UserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"


# --------------------------------------------------
# Get All Users
# --------------------------------------------------

@router.get("/")
def get_users():

    db = SessionLocal()

    try:
        users = (
            db.query(User)
            .order_by(User.id.asc())
            .all()
        )

        return [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
            for user in users
        ]

    finally:
        db.close()


# --------------------------------------------------
# Add User
# --------------------------------------------------

@router.post("/")
def add_user(user_data: UserRequest):

    db = SessionLocal()

    try:

        existing_user = (
            db.query(User)
            .filter(User.email == user_data.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="User with this email already exists."
            )

        new_user = User(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User Added Successfully",
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
# Update User
# --------------------------------------------------

@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_data: UserRequest
):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # Check duplicate email
        duplicate = (
            db.query(User)
            .filter(
                User.email == user_data.email,
                User.id != user_id
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Another user already uses this email."
            )

        user.name = user_data.name
        user.email = user_data.email
        user.password = user_data.password
        user.role = user_data.role

        db.commit()
        db.refresh(user)

        return {
            "message": "User Updated Successfully",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }

    finally:
        db.close()


# --------------------------------------------------
# Delete User
# --------------------------------------------------

@router.delete("/{user_id}")
def delete_user(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        db.delete(user)
        db.commit()

        return {
            "message": "User Deleted Successfully"
        }

    finally:
        db.close()