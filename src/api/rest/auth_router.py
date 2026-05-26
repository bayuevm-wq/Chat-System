"""
Authentication REST API router.

Endpoints for user registration, login, token refresh, logout,
and WebSocket token generation.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter

from src.api.dependencies import AuthServiceDep, CurrentUser

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Request/Response Schemas ────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class AuthResponse(BaseModel):
    user: dict
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class WSTokenResponse(BaseModel):
    ws_token: str


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, auth_service: AuthServiceDep):
    """Register a new user account."""
    result = await auth_service.register(
        username=body.username,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
    )
    return AuthResponse(**result, token_type="bearer")


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, auth_service: AuthServiceDep):
    """Authenticate with email and password."""
    result = await auth_service.login(email=body.email, password=body.password)
    return AuthResponse(**result, token_type="bearer")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, auth_service: AuthServiceDep):
    """Exchange a refresh token for a new access token."""
    result = await auth_service.refresh_token(body.refresh_token)
    return TokenResponse(**result)


@router.post("/logout", status_code=204)
async def logout(current_user: CurrentUser, auth_service: AuthServiceDep):
    """Revoke the current token."""
    await auth_service.logout(current_user.get("jti", ""))


@router.post("/ws-token", response_model=WSTokenResponse)
async def get_ws_token(current_user: CurrentUser, auth_service: AuthServiceDep):
    """Get a short-lived token for WebSocket authentication."""
    ws_token = await auth_service.get_ws_token(current_user["sub"])
    return WSTokenResponse(ws_token=ws_token)
