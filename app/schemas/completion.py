"""Pydantic schemas for Completion model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompletionCreate(BaseModel):
    """Schema for creating a new completion (marking task as done)."""
    # task_id will come from the URL path parameter
    pass


class CompletionResponse(BaseModel):
    """Schema for completion responses."""
    id: int
    task_id: int
    user_id: int
    group_id: int
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompletionWithUser(CompletionResponse):
    """Schema for completion with user information."""
    user_name: str
    user_email: str
