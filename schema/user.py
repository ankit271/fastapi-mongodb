from datetime import datetime
from typing import Optional, List
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict
)
import re


class UserModelConfig:
    """Configuration for User model"""
    CONFIG = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "signup_ts": "2023-01-01T00:00:00",
                "roles": ["user", "editor"]
            }]
        }
    )


class UserValidation:
    """User validation rules and constants"""
    USERNAME_PATTERN = r'^[a-zA-Z0-9_]+$'
    ALLOWED_ROLES = {"admin", "user", "editor", "viewer"}
    USERNAME_MIN_LENGTH = 3
    USERNAME_MAX_LENGTH = 50
    FULLNAME_MAX_LENGTH = 100
    ANONYMOUS_USERNAME = "anonymous"

    @classmethod
    def validate_username_format(cls, username: str) -> str:
        if not re.match(cls.USERNAME_PATTERN, username):
            raise ValueError('Username must be alphanumeric with underscores only')
        return username

    @classmethod
    def validate_roles(cls, roles: List[str]) -> List[str]:
        invalid_roles = set(roles) - cls.ALLOWED_ROLES
        if invalid_roles:
            raise ValueError(
                f"Invalid roles: {', '.join(invalid_roles)}. "
                f"Must be one of: {', '.join(cls.ALLOWED_ROLES)}")
        return roles


class User(BaseModel):
    model_config = UserModelConfig.CONFIG

    username: str = Field(
        ...,
        min_length=UserValidation.USERNAME_MIN_LENGTH,
        max_length=UserValidation.USERNAME_MAX_LENGTH,
        description="Username for login"
    )
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(
        default="",
        max_length=UserValidation.FULLNAME_MAX_LENGTH,
        description="User's full name"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active"
    )
    signup_ts: Optional[datetime] = Field(
        None,
        description="Timestamp when user signed up"
    )
    roles: List[str] = Field(
        default_factory=list,
        description="User roles for permission management"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        return UserValidation.validate_username_format(v)

    @field_validator('roles')
    @classmethod
    def validate_user_roles(cls, v: List[str]) -> List[str]:
        return UserValidation.validate_roles(v)

    @model_validator(mode='after')
    def validate_name_requirements(self) -> 'User':
        if not self.full_name and self.username == UserValidation.ANONYMOUS_USERNAME:
            raise ValueError(
                "Either full_name or a non-anonymous username must be provided")
        return self


class UserResponse(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    roles: List[str]
