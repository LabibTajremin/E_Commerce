from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterTenantOwnerRequest(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=255)
    subdomain: str = Field(min_length=1, max_length=63)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=255)


class RegisterTenantOwnerResponse(BaseModel):
    tenant_id: UUID
    owner_id: UUID
    subdomain: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
