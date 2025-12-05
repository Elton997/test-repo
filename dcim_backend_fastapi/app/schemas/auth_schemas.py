# app/schemas/auth_schemas.py
"""
Authentication and RBAC schemas matching the updated models.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    name: str = Field(..., description="Username (unique)")


class UserCreate(UserBase):
    email: EmailStr = Field(..., description="User email (unique)")
    full_name: Optional[str] = Field(None, description="User's full name")
    description: Optional[str] = Field(None, max_length=255)


class UserRead(UserBase):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Username")
    email: Optional[EmailStr] = Field(None, description="User email")
    full_name: Optional[str] = Field(None, description="User's full name")
    is_active: Optional[bool] = Field(None, description="Is user active")
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Token Schemas
# =============================================================================

class TokenRead(BaseModel):
    id: int
    token_key: str
    expires: Optional[datetime] = None
    created: datetime
    last_used: Optional[datetime] = None
    token_type: Optional[str] = None

    class Config:
        from_attributes = True


class ConfigureFlags(BaseModel):
    is_editable: bool = False
    is_deletable: bool = False
    is_viewer: bool = False


class LoginResponse(BaseModel):
    # JWT access token – signed using settings.JWT_SECRET_KEY / JWT_ALGORITHM
    access_token: str
    # Opaque refresh token key stored in the database
    refresh_token: str
    user: UserRead
    menuList: Optional[list] = None
    configure: ConfigureFlags = Field(default_factory=ConfigureFlags)


# =============================================================================
# Role Schemas
# =============================================================================

class RoleBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=255)


class RoleCreate(RoleBase):
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(None, max_length=255)


class RoleRead(RoleBase):
    id: int
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# UserRole Schemas
# =============================================================================

class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int
    description: Optional[str] = Field(None, max_length=255)


class UserRoleRead(BaseModel):
    id: int
    user_id: int
    role_id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Menu Schemas (formerly Module)
# =============================================================================

class MenuBase(BaseModel):
    header_name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=255)


class MenuCreate(MenuBase):
    icon: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(None, max_length=255)


class MenuRead(MenuBase):
    id: int
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class MenuUpdate(BaseModel):
    header_name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=255)
    icon: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# SubMenu Schemas (formerly Submodule)
# =============================================================================

class SubMenuBase(BaseModel):
    display_name: str = Field(..., max_length=255)
    page_url: str = Field(..., max_length=255)
    code: str = Field(..., max_length=255)


class SubMenuCreate(SubMenuBase):
    menu_id: int
    icon: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(None, max_length=255)


class SubMenuRead(SubMenuBase):
    id: int
    menu_id: int
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SubMenuUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    page_url: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=255)
    menu_id: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# RoleSubMenuAccess Schemas (formerly RoleSubmoduleAccess)
# =============================================================================

class RoleSubMenuAccessCreate(BaseModel):
    role_id: int
    sub_menu_id: int
    can_view: bool = Field(default=True)
    description: Optional[str] = Field(None, max_length=255)


class RoleSubMenuAccessRead(BaseModel):
    role_id: int
    sub_menu_id: int
    can_view: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleSubMenuAccessUpdate(BaseModel):
    can_view: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# AuditLog Schemas
# =============================================================================

class AuditLogRead(BaseModel):
    id: int
    time: datetime
    user_id: Optional[int] = None
    action: str
    type: str
    object_id: Optional[int] = None
    message: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Environment Schemas
# =============================================================================

class EnvironmentBase(BaseModel):
    name: str = Field(..., max_length=255)
    env_code: str = Field(..., max_length=64)


class EnvironmentCreate(EnvironmentBase):
    description: Optional[str] = Field(None, max_length=255)


class EnvironmentRead(EnvironmentBase):
    id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    env_code: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
