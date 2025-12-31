"""Pydantic schemas for Task model."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class TaskBase(BaseModel):
    """Base task schema with common fields."""
    name: str
    emoji: Optional[str] = None
    category: Optional[str] = None


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    assigned_user_ids: Optional[List[int]] = None


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
    assigned_user_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def extract_assigned_users(cls, data: Any) -> Any:
        """Extract user IDs from assigned_users relationship."""
        if isinstance(data, dict):
            return data

        # Data is a SQLAlchemy model object (Task)
        if hasattr(data, 'assigned_users'):
            # Create a dict from the model attributes
            result = {}
            for field in ['id', 'name', 'emoji', 'category', 'group_id', 'created_at', 'is_active']:
                if hasattr(data, field):
                    result[field] = getattr(data, field)

            # Extract assigned user IDs
            assigned_users = getattr(data, 'assigned_users', [])
            result['assigned_user_ids'] = [user.id for user in assigned_users]

            return result

        return data


class TaskAssignmentUpdate(BaseModel):
    """Schema for updating task assignments."""
    assigned_user_ids: List[int]

    model_config = ConfigDict(from_attributes=True)
