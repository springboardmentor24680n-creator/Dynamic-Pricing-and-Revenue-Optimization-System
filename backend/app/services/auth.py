"""
PricePilot AI - Auth Service
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional
import secrets

from app.models.user import User
from app.models.access_request import AccessRequest
from app.schemas.user import UserCreate, ROLES
from app.utils import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    create_password_reset_token, verify_password_reset_token,
    decode_refresh_token,
)
from app.services.activity_service import ActivityService

APPROVAL_PENDING_MESSAGE = (
    "Your identity has been verified successfully, but your account requires "
    "administrator approval before accessing PricePilot AI. Your request has "
    "been sent to the administrator."
)


def is_approved(user: User) -> bool:
    """A user may sign in only when approval_status is approved (or legacy NULL)."""
    return user.approval_status in (None, "approved")


class AuthService:
    """Service for user authentication and registration."""
    
    def __init__(self, db: Session):
        self.db = db

    def _pending_payload(self, user: User, provider: str = "local") -> dict:
        """Response payload for a user whose account awaits approval.

        Never contains tokens - pending users must not obtain JWT access.
        """
        return {
            "access_pending": True,
            "status": "pending",
            "email": user.email,
            "name": user.full_name or user.username,
            "provider": provider,
            "message": APPROVAL_PENDING_MESSAGE,
        }

    def _ensure_access_request(self, email: str, name: str, provider: str,
                               requested_role: str = "data_analyst",
                               reason: str = None) -> AccessRequest:
        """Create a pending access request if one does not already exist."""
        existing = (
            self.db.query(AccessRequest)
            .filter(
                AccessRequest.email == email,
                AccessRequest.status == "Pending",
            )
            .first()
        )
        if existing:
            if reason and not existing.reason:
                existing.reason = reason
                self.db.commit()
            return existing
        access_request = AccessRequest(
            email=email,
            name=name,
            provider=provider,
            requested_role=requested_role,
            reason=reason,
            status="Pending",
        )
        self.db.add(access_request)
        self.db.commit()
        self.db.refresh(access_request)
        return access_request

    def _issue_tokens(self, user: User) -> dict:
        """Issue access + refresh token pair for a user."""
        access_token = create_access_token(data={"user_id": user.id, "role": user.role})
        refresh_token = create_refresh_token(data={"user_id": user.id, "role": user.role})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": self._user_payload(user),
        }

    def _user_payload(self, user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "google_id": user.google_id,
            "profile_picture": user.profile_picture,
            "is_google_user": user.is_google_user,
            "avatar_url": user.avatar_url,
            "notifications_enabled": user.notifications_enabled,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    
    def register(self, user_data: UserCreate) -> User:
        """Register a new user."""
        existing = (
            self.db.query(User)
            .filter((User.email == user_data.email) | (User.username == user_data.username))
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email or username already exists",
            )
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            approval_status="approved",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def request_access(self, user_data: UserCreate) -> dict:
        """Public self-registration under the approval workflow.

        Creates a pending (inactive) user account and an AccessRequest row. No
        tokens are issued and the account cannot sign in until an administrator
        approves the request. Admin-created users go through ``register()``
        instead and are approved immediately.

        Re-request flow: a previously REJECTED user may register again (same
        email or username). The account is reset to pending and a fresh access
        request is created so the administrator can review it anew.
        """
        existing = (
            self.db.query(User)
            .filter((User.email == user_data.email) | (User.username == user_data.username))
            .first()
        )
        if existing:
            if is_approved(existing):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email or username already exists",
                )
            if existing.approval_status == "rejected":
                # Re-request: reset to pending, update details, fresh request.
                # The OR-query above guarantees the new username (if different)
                # doesn't collide with another account, so it's safe to adopt it.
                existing.username = user_data.username
                existing.approval_status = "pending"
                existing.is_active = False
                existing.full_name = user_data.full_name or existing.full_name
                existing.hashed_password = hash_password(user_data.password)
                existing.role = user_data.role or "data_analyst"
                self.db.commit()
                self._ensure_access_request(
                    existing.email, existing.full_name or existing.username, "local",
                    requested_role=existing.role, reason=user_data.reason,
                )
                return self._pending_payload(existing)
            # Pending - refresh the access request so the admin sees the latest attempt
            self._ensure_access_request(
                existing.email, existing.full_name or existing.username, "local",
                requested_role=existing.role, reason=user_data.reason,
            )
            return self._pending_payload(existing)

        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
            role=user_data.role or "data_analyst",
            is_active=False,            # not active until approved
            approval_status="pending",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self._ensure_access_request(
            user.email, user.full_name or user.username, "local",
            requested_role=user.role, reason=user_data.reason,
        )
        return self._pending_payload(user)

    def login(self, username: str, password: str) -> dict:
        """Authenticate a user and return token pair.

        Identity is always verified first. Pending users receive an
        ``access_pending`` payload (no tokens) and rejected users are blocked.
        """
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if user.approval_status == "pending":
            self._ensure_access_request(user.email, user.full_name or user.username, "local", requested_role=user.role)
            return self._pending_payload(user)
        if user.approval_status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access request was rejected by the administrator. You can request access again on the sign-up page.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new access token."""
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        user_id = payload.get("user_id")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or not is_approved(user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return self._issue_tokens(user)

    def change_password(self, user: User, current_password: str, new_password: str) -> dict:
        """Change the current user's password after verifying the current one."""
        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account uses Google sign-in and has no password to change",
            )
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters",
            )
        user.hashed_password = hash_password(new_password)
        self.db.commit()
        return {"message": "Password changed successfully"}

    def update_profile(self, user: User, full_name: str = None, email: str = None,
                       notifications_enabled: bool = None) -> User:
        """Update the current user's profile."""
        if full_name is not None:
            user.full_name = full_name
        if email is not None and email != user.email:
            existing = self.db.query(User).filter(User.email == email, User.id != user.id).first()
            if existing:
                raise HTTPException(status_code=409, detail="Email already in use")
            user.email = email
        if notifications_enabled is not None:
            user.notifications_enabled = notifications_enabled
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def google_login(self, email: str, google_id: str, name: str, picture: str = "") -> dict:
        """Authenticate a user via a verified Google profile.

        Google sign-in is available to all approved users regardless of role.
        The user's existing database role is preserved — Google authentication
        never creates accounts or changes roles. Pending users receive an
        ``access_pending`` response (no tokens) and rejected users are blocked.
        The caller (router layer) is responsible for verifying the Google ID
        token server-side before calling this method.
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No account found for this Google email. Please sign up with your email and password first, or contact your administrator.",
            )
        if user.approval_status == "pending":
            self._ensure_access_request(user.email, user.full_name or user.username, "google", requested_role=user.role)
            return self._pending_payload(user, provider="google")
        if user.approval_status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access request was rejected by the administrator. You can request access again on the sign-up page.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        # Approved, active user of any role: link the Google identity if not already linked
        if user.google_id != google_id:
            user.google_id = google_id
        if picture and user.profile_picture != picture:
            user.profile_picture = picture
            user.avatar_url = picture
        if not user.is_google_user:
            user.is_google_user = True
        self.db.commit()
        self.db.refresh(user)
        return self._issue_tokens(user)
    
    def forgot_password(self, email: str) -> dict:
        """Generate a password reset token for the given email."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal whether the email exists
            return {
                "message": "If an account with that email exists, a reset link has been generated.",
                "reset_token": None,
            }
        
        reset_token = create_password_reset_token(user.id, user.email)
        
        return {
            "message": "If an account with that email exists, a reset link has been generated.",
            "reset_token": reset_token,
        }
    
    def reset_password(self, token: str, new_password: str) -> dict:
        """Reset password using a valid reset token."""
        payload = verify_password_reset_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        
        user_id = payload.get("user_id")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters",
            )
        
        user.hashed_password = hash_password(new_password)
        self.db.commit()
        
        return {"message": "Password has been reset successfully. You can now sign in."}

    def admin_reset_password(self, admin, user_id: int, new_password: str) -> dict:
        """Admin resets another user's password."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        user.hashed_password = hash_password(new_password)
        self.db.commit()
        return {"message": f"Password reset for {user.username}"}

    def update_user(self, admin, user_id: int, full_name: str = None, role: str = None,
                    email: str = None, is_active: bool = None) -> User:
        """Admin updates another user's details or role."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if role is not None:
            if role not in ROLES:
                raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLES)}")
            user.role = role
        if full_name is not None:
            user.full_name = full_name
        if email is not None and email != user.email:
            existing = self.db.query(User).filter(User.email == email, User.id != user_id).first()
            if existing:
                raise HTTPException(status_code=409, detail="Email already in use")
            user.email = email
        if is_active is not None:
            if user.id == admin.id and is_active is False:
                raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
            user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_user_by_id(self, user_id: int) -> User:
        """Get a user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
