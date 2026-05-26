"""
Users REST API router.

Endpoints for user profile and presence status.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from src.api.dependencies import CurrentUser, PresenceServiceDep, UserRepo

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me")
async def get_current_user_profile(current_user: CurrentUser, user_repo: UserRepo):
    """Get the current authenticated user's profile."""
    user = await user_repo.get_by_id(UUID(current_user["sub"]))
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/{user_id}")
async def get_user_profile(user_id: UUID, current_user: CurrentUser, user_repo: UserRepo):
    """Get a user's public profile."""
    user = await user_repo.get_by_id(user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


@router.get("/{user_id}/presence")
async def get_user_presence(
    user_id: UUID,
    current_user: CurrentUser,
    presence_service: PresenceServiceDep,
):
    """Get a user's presence status."""
    return await presence_service.get_status(str(user_id))
