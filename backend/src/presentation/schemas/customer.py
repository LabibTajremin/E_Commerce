from pydantic import BaseModel, EmailStr, Field


class RegisterCustomerRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    name: str = Field(min_length=1, max_length=255)


class LoginCustomerRequest(BaseModel):
    email: EmailStr
    password: str
