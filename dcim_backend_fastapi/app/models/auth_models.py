# app/models/auth_models.py
"""
Authentication and RBAC models matching Alembic migrations.
All tables use 'dcim' schema with lowercase column names.
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.entity_models import Location

from app.db.base import Base


class User(Base):
    """
    Maps to dcim.dcim_user table.
    Migration: 001_create_dcim_user
    """
    __tablename__ = "dcim_user"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    description = Column(String(255), nullable=True)

    # Relationships
    tokens = relationship(
        "Token",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    user_roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
    )
    location_accesses = relationship(
        "UserLocationAccess",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Token(Base):
    """
    Maps to dcim.dcim_user_token table.
    Migration: 002_create_dcim_user_token
    """
    __tablename__ = "dcim_user_token"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_key = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(
        Integer,
        ForeignKey("dcim.dcim_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    description = Column(String(255), nullable=True)
    token_type = Column(String(10), nullable=True)  # "access" or "refresh"

    user = relationship("User", back_populates="tokens")


class Role(Base):
    """
    Maps to dcim.dcim_rbac_role table.
    Migration: 017_create_dcim_rbac_role
    """
    __tablename__ = "dcim_rbac_role"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)

    user_roles = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    sub_menu_accesses = relationship(
        "RoleSubMenuAccess",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class UserRole(Base):
    """
    Maps to dcim.dcim_rbac_user_role table.
    Migration: 018_create_dcim_rbac_user_role
    Many-to-many relationship between users and roles.
    """
    __tablename__ = "dcim_rbac_user_role"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("dcim.dcim_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        Integer,
        ForeignKey("dcim.dcim_rbac_role.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(255), nullable=True)

    role = relationship("Role", back_populates="user_roles")
    user = relationship("User", back_populates="user_roles")


class Menu(Base):
    """
    Maps to dcim.dcim_menu table.
    Migration: 019_create_dcim_menu
    """
    __tablename__ = "dcim_menu"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    header_name = Column(String(255), nullable=False)
    icon = Column(String(255), nullable=True)
    code = Column(String(255), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)

    sub_menus = relationship("SubMenu", back_populates="menu")


class SubMenu(Base):
    """
    Maps to dcim.dcim_sub_menu table.
    Migration: 020_create_dcim_sub_menu
    """
    __tablename__ = "dcim_sub_menu"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(
        Integer,
        ForeignKey("dcim.dcim_menu.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(255), nullable=False)
    page_url = Column(String(255), nullable=False)
    icon = Column(String(255), nullable=True)
    code = Column(String(255), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)

    menu = relationship("Menu", back_populates="sub_menus")
    access = relationship("RoleSubMenuAccess", back_populates="sub_menu")


class RoleSubMenuAccess(Base):
    """
    Maps to dcim.dcim_rbac_role_sub_menu_access table.
    Migration: 021_create_dcim_rbac_role_sub_menu_access
    Composite primary key (role_id, sub_menu_id).
    """
    __tablename__ = "dcim_rbac_role_sub_menu_access"
    __table_args__ = {"schema": "dcim"}

    role_id = Column(
        Integer,
        ForeignKey("dcim.dcim_rbac_role.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    sub_menu_id = Column(
        Integer,
        ForeignKey("dcim.dcim_sub_menu.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    can_view = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)

    role = relationship("Role", back_populates="sub_menu_accesses")
    sub_menu = relationship("SubMenu", back_populates="access")


class AuditLog(Base):
    """
    Maps to dcim.dcim_audit_log table.
    Migration: 015_create_dcim_audit_log
    Tracks all entity changes (create, update, delete).
    """
    __tablename__ = "dcim_audit_log"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(
        Integer,
        ForeignKey("dcim.dcim_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(255), nullable=False)  # "create", "update", "delete"
    type = Column(String(255), nullable=False, index=True)  # entity type: "rack", "device", etc.
    object_id = Column(Integer, nullable=True)  # ID of the affected object
    message = Column(Text, nullable=True)  # additional details/JSON
    description = Column(String(255), nullable=True)

    user = relationship("User", back_populates="audit_logs")


class UserLocationAccess(Base):
    """
    Maps to dcim.dcim_user_location_access table.
    Stores per-user allowed locations for RBAC scoping.
    """

    __tablename__ = "dcim_user_location_access"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("dcim.dcim_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user = relationship("User", back_populates="location_accesses")
    location = relationship(Location)


class Environment(Base):
    """
    Maps to dcim.dcim_environment table.
    Migration: 016_create_dcim_environment
    """
    __tablename__ = "dcim_environment"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    env_code = Column(String(64), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
