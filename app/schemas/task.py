"""Pydantic schemas for Task model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    """Base task schema with common fields."""
    name: str
    emoji: Optional[str] = None
    category: Optional[str] = None


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating task information."""
    name: Optional[str] = None
    emoji: Optional[str] = None
    category: Optional[str] = None


class TaskResponse(TaskBase):
    """Schema for task responses."""
    id: int
    group_id: int
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
