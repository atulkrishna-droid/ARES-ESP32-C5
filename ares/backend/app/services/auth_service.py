"""Authentication and RBAC Authorization Service."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.constants import RoleType
from app.core.exceptions import AuthenticationFailedException, PermissionDeniedException, ResourceNotFoundException
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.user import Permission, Role, User
from app.schemas.auth import TokenResponse, UserRegisterRequest
from app.services.audit_service import AuditService


class AuthService:
    @staticmethod
    def register(db: Session, request: UserRegisterRequest, actor_id: Optional[str] = None) -> User:
        existing = db.query(User).filter((User.username == request.username) | (User.email == request.email)).first()
        if existing:
            raise AuthenticationFailedException("A user with this username or email already exists.")

        user = User(
            email=request.email,
            username=request.username,
            password_hash=hash_password(request.password),
            display_name=request.display_name or request.username,
            is_active=True,
            is_verified=True,
        )

        # Assign role
        role_name = request.role or RoleType.ANALYST.value
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            # Create default role if it doesn't exist
            role = Role(name=role_name, description=f"Default {role_name} role")
            db.add(role)
            db.flush()

        user.roles.append(role)
        db.add(user)
        db.commit()
        db.refresh(user)

        AuditService.record_event(
            db=db,
            action="USER_REGISTERED",
            resource_type="USER",
            resource_id=user.id,
            actor_id=actor_id or user.id,
            metadata={"username": user.username, "roles": [r.name for r in user.roles]},
        )
        return user

    @staticmethod
    def login(db: Session, username_or_email: str, password: str) -> TokenResponse:
        user = db.query(User).filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationFailedException("Invalid username or password.")

        if not user.is_active:
            raise AuthenticationFailedException("This account has been deactivated.")

        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

        roles = [r.name for r in user.roles]
        permissions = user.permission_names

        access_token = create_access_token(subject=user.id, roles=roles, permissions=permissions)
        refresh_token = create_refresh_token(subject=user.id)

        AuditService.record_event(
            db=db,
            action="USER_LOGIN_SUCCESS",
            resource_type="USER",
            resource_id=user.id,
            actor_id=user.id,
            metadata={"username": user.username},
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,
            user_id=user.id,
            username=user.username,
            roles=roles,
            permissions=permissions,
        )

    @staticmethod
    def refresh(db: Session, refresh_token: str) -> TokenResponse:
        from app.core.security import is_token_revoked, revoke_token
        if is_token_revoked(refresh_token):
            raise AuthenticationFailedException("Refresh token has been revoked or already rotated.")

        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthenticationFailedException("Invalid token type.")
            user_id = payload.get("sub")
        except Exception:
            raise AuthenticationFailedException("Invalid or expired refresh token.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise AuthenticationFailedException("User not found or inactive.")

        # Invalidate old refresh token (Strict rotation enforcement)
        revoke_token(refresh_token)

        roles = [r.name for r in user.roles]
        permissions = user.permission_names
        new_access_token = create_access_token(subject=user.id, roles=roles, permissions=permissions)
        new_refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=1800,
            user_id=user.id,
            username=user.username,
            roles=roles,
            permissions=permissions,
        )

    @classmethod
    def refresh_access_token(cls, db: Session, refresh_token: str) -> TokenResponse:
        return cls.refresh(db, refresh_token)

    @staticmethod
    def logout(db: Session, refresh_token: str) -> None:
        from app.core.security import revoke_token
        revoke_token(refresh_token)
