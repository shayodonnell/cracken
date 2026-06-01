"""Task completion logic endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_current_group_member
from app.database import get_db
from app.models.completion import Completion
from app.models.task import Task
from app.models.group import Group
from app.models.user import User
from app.schemas.completion import CompletionResponse, CompletionWithUser

router = APIRouter()


@router.post(
    "/{task_id}",
    response_model=CompletionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Could not validate credentials"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Group not found / Task not found"},
        400: {"description": "Cannot complete an inactive task"}
    }
)
def mark_task_complete(
    group_id: int,
    task_id: int,
    _group: Group = Depends(get_current_group_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a task as complete by the current user.

    Creates a completion record tracking that the authenticated user
    completed the specified task. The task must exist, belong to the
    specified group, and be active.

    Args:
        group_id: ID of the group
        task_id: ID of the task to mark complete
        group: Group object (verified via dependency)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created completion record

    Raises:
        HTTPException: 404 if task not found, 400 if task is inactive,
                      403 if not a group member
    """
    # Get task and validate it belongs to the group
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.group_id == group_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task is active
    if not task.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete an inactive task"
        )

    # Create completion record
    completion = Completion(
        task_id=task_id,
        user_id=current_user.id,
        group_id=group_id  # Denormalized for query performance
    )

    db.add(completion)
    db.commit()
    db.refresh(completion)

    return completion


@router.get(
    "",
    response_model=List[CompletionWithUser],
    responses={
        401: {"description": "Could not validate credentials"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Group not found"}
    }
)
def list_group_completions(
    group_id: int,
    task_id: Optional[int] = Query(None, description="Filter by specific task"),
    user_id: Optional[int] = Query(None, description="Filter by specific user"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max number of records to return"),
    _group: Group = Depends(get_current_group_member),
    db: Session = Depends(get_db)
):
    """
    List all completions in a group with optional filters.

    Returns completions ordered by most recent first. Supports filtering
    by task or user, and pagination via skip/limit parameters.

    Args:
        group_id: ID of the group
        task_id: Optional filter by specific task
        user_id: Optional filter by specific user
        skip: Number of records to skip (for pagination)
        limit: Max records to return (max 100)
        group: Group object (verified via dependency)
        db: Database session

    Returns:
        List of completions with user information

    Raises:
        HTTPException: 403 if not a group member
    """
    # Build base query with eager loading of user data
    query = db.query(Completion).options(
        joinedload(Completion.user)
    ).filter(Completion.group_id == group_id)

    # Apply optional filters
    if task_id is not None:
        query = query.filter(Completion.task_id == task_id)

    if user_id is not None:
        query = query.filter(Completion.user_id == user_id)

    # Order by most recent first and apply pagination
    completions = query.order_by(
        Completion.completed_at.desc()
    ).offset(skip).limit(limit).all()

    # Construct response with user data
    completions_with_users = [
        CompletionWithUser(
            id=c.id,
            task_id=c.task_id,
            user_id=c.user_id,
            group_id=c.group_id,
            completed_at=c.completed_at,
            user_name=c.user.name,
            user_email=c.user.email
        )
        for c in completions
    ]

    return completions_with_users


@router.get(
    "/tasks/{task_id}",
    response_model=List[CompletionWithUser],
    responses={
        401: {"description": "Could not validate credentials"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Group not found / Task not found"}
    }
)
def get_task_completion_history(
    group_id: int,
    task_id: int,
    limit: int = Query(10, ge=1, le=50, description="Number of recent completions to return"),
    _group: Group = Depends(get_current_group_member),
    db: Session = Depends(get_db)
):
    """
    Get completion history for a specific task.

    Returns the most recent completions for a task, showing who completed
    it and when. Useful for viewing rotation history and determining whose
    turn it is next.

    Args:
        group_id: ID of the group
        task_id: ID of the task
        limit: Number of recent completions to return (max 50)
        group: Group object (verified via dependency)
        db: Database session

    Returns:
        List of completions with user information, ordered by most recent

    Raises:
        HTTPException: 404 if task not found, 403 if not a group member
    """
    # Verify task exists and belongs to group
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.group_id == group_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get completions with user data
    completions = db.query(Completion).options(
        joinedload(Completion.user)
    ).filter(
        Completion.task_id == task_id,
        Completion.group_id == group_id
    ).order_by(
        Completion.completed_at.desc()
    ).limit(limit).all()

    # Construct response with user data
    completions_with_users = [
        CompletionWithUser(
            id=c.id,
            task_id=c.task_id,
            user_id=c.user_id,
            group_id=c.group_id,
            completed_at=c.completed_at,
            user_name=c.user.name,
            user_email=c.user.email
        )
        for c in completions
    ]

    return completions_with_users
