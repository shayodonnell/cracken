"""Pydantic schemas for Group model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class GroupBase(BaseModel):
    """Base group schema with common fields."""
    name: str


class GroupCreate(GroupBase):
    """Schema for creating a new group."""
    pass


class GroupUpdate(BaseModel):
    """Schema for updating group information."""
    name: Optional[str] = None


class GroupResponse(GroupBase):
    """Schema for group responses."""
    id: int
    invite_code: str
    created_at: datetime
    created_by: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class GroupJoin(BaseModel):
    """Schema for joining a group via invite code."""
    invite_code: str


class GroupMemberResponse(BaseModel):
    """Schema for group member information."""
    id: int
    email: str
    name: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
