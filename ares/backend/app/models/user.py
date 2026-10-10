"""User, Role, and Permission models for Granular RBAC."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    permissions = relationship("Permission", secondary=role_permissions, backref="roles", lazy="joined")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    roles = relationship("Role", secondary=user_roles, backref="users", lazy="joined")

    def has_permission(self, permission_name: str) -> bool:
        for role in self.roles:
            for perm in role.permissions:
                if perm.name == permission_name or perm.name == "*":
                    return True
        return False

    @property
    def permission_names(self) -> list[str]:
        perms = set()
        for role in self.roles:
            for perm in role.permissions:
                perms.add(perm.name)
        return sorted(list(perms))

    @property
    def role_names(self) -> list[str]:
        return [r.name for r in self.roles]
