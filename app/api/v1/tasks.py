"""Task management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.task import Task
from app.models.group import Group, group_members
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()


def verify_group_membership_for_tasks(group_id: int, user_id: int, db: Session) -> Group:
    """
    Verify user is a member of a group.

    Args:
        group_id: Group ID
        user_id: User ID
        db: Database session

    Returns:
        Group object if user is a member

    Raises:
        HTTPException: 404 if group not found, 403 if not a member
    """
    # Check group exists
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check membership
    membership = db.execute(
        select(group_members).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )

    return group


def verify_admin_role(group_id: int, user_id: int, db: Session) -> None:
    """
    Verify user is an admin of a group.

    Args:
        group_id: Group ID
        user_id: User ID
        db: Database session

    Raises:
        HTTPException: 403 if not an admin
    """
    role = db.execute(
        select(group_members.c.role).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id
        )
    ).scalar()

    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group admins can perform this action"
        )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    group_id: int,
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task in a group.

    Any member of the group can create tasks.

    Args:
        group_id: ID of the group
        task_data: Task creation data (name, emoji, category)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created task with all fields

    Raises:
        HTTPException: 404 if group not found, 403 if not a member
    """
    # Verify membership
    verify_group_membership_for_tasks(group_id, current_user.id, db)

    # Create task
    new_task = Task(
        name=task_data.name,
        emoji=task_data.emoji,
        category=task_data.category,
        group_id=group_id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    group_id: int,
    include_inactive: bool = Query(False, description="Include soft-deleted tasks"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all tasks in a group.

    By default, only active tasks are returned. Use include_inactive=true
    to also see soft-deleted tasks.

    Args:
        group_id: ID of the group
        include_inactive: Whether to include inactive (deleted) tasks
        current_user: Authenticated user
        db: Database session

    Returns:
        List of tasks in the group

    Raises:
        HTTPException: 404 if group not found, 403 if not a member
    """
    # Verify membership
    verify_group_membership_for_tasks(group_id, current_user.id, db)

    # Build query
    query = db.query(Task).filter(Task.group_id == group_id)

    # Filter by active status
    if not include_inactive:
        query = query.filter(Task.is_active == True)

    # Order by created date (newest first)
    tasks = query.order_by(Task.created_at.desc()).all()

    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    group_id: int,
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific task.

    Args:
        group_id: ID of the group
        task_id: ID of the task
        current_user: Authenticated user
        db: Database session

    Returns:
        Task details

    Raises:
        HTTPException: 404 if group/task not found, 403 if not a member
    """
    # Verify membership
    verify_group_membership_for_tasks(group_id, current_user.id, db)

    # Get task
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.group_id == group_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    group_id: int,
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a task's details.

    Any member can update any task in the group. Only provided fields
    will be updated (partial update).

    Args:
        group_id: ID of the group
        task_id: ID of the task
        task_data: Fields to update (name, emoji, category)
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if group/task not found, 403 if not a member
    """
    # Verify membership
    verify_group_membership_for_tasks(group_id, current_user.id, db)

    # Get task
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.group_id == group_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update provided fields (exclude_unset=True skips None values)
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    group_id: int,
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a task.

    Only admins can delete tasks. This is a soft delete - the task
    is marked as inactive (is_active=False) but not physically removed.
    Completion history is preserved.

    Args:
        group_id: ID of the group
        task_id: ID of the task
        current_user: Authenticated user (must be admin)
        db: Database session

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if group/task not found, 403 if not admin
    """
    # Verify membership
    verify_group_membership_for_tasks(group_id, current_user.id, db)

    # Verify admin role
    verify_admin_role(group_id, current_user.id, db)

    # Get task
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.group_id == group_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Soft delete
    task.is_active = False
    db.commit()

    return None
