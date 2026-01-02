"""Task management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_group_member
from app.database import get_db
from app.models.task import Task, task_assignments
from app.models.group import Group, group_members
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskAssignmentUpdate

router = APIRouter()

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
    group: Group = Depends(get_current_group_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task in a group.

    Any member of the group can create tasks. By default, tasks are assigned
    to all current group members. Optionally specify assigned_user_ids to
    assign to specific members only.

    Args:
        group_id: ID of the group
        task_data: Task creation data (name, emoji, category, assigned_user_ids)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created task with assigned users

    Raises:
        HTTPException: 404 if group not found, 403 if not a member,
                      400 if assigned_user_ids contains non-members
    """
    # Determine who to assign the task to
    if task_data.assigned_user_ids is None:
        # Default: assign to all current group members
        assigned_user_ids = [member.id for member in group.members]
    else:
        # Use provided list (can be empty)
        assigned_user_ids = task_data.assigned_user_ids

    # Validate: all assigned users must be group members
    if assigned_user_ids:
        group_member_ids = {member.id for member in group.members}
        invalid_ids = set(assigned_user_ids) - group_member_ids

        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Users {list(invalid_ids)} are not members of this group"
            )

    # Create task
    new_task = Task(
        name=task_data.name,
        emoji=task_data.emoji,
        category=task_data.category,
        group_id=group_id
    )

    db.add(new_task)
    db.flush()  # Get task.id before adding assignments

    # Add assignments
    if assigned_user_ids:
        for user_id in assigned_user_ids:
            db.execute(
                task_assignments.insert().values(
                    task_id=new_task.id,
                    user_id=user_id
                )
            )

    db.commit()
    db.refresh(new_task)

    return new_task


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    group_id: int,
    include_inactive: bool = Query(False, description="Include soft-deleted tasks"),
    group: Group = Depends(get_current_group_member),
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
    group: Group = Depends(get_current_group_member),
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
    group: Group = Depends(get_current_group_member),
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


@router.put("/{task_id}/assignments", response_model=TaskResponse)
def update_task_assignments(
    group_id: int,
    task_id: int,
    assignment_data: TaskAssignmentUpdate,
    group: Group = Depends(get_current_group_member),
    db: Session = Depends(get_db)
):
    """
    Update which users are assigned to a task.

    Any member can update task assignments. This completely replaces
    existing assignments with the new list.

    Args:
        group_id: ID of the group
        task_id: ID of the task
        assignment_data: New list of user IDs to assign
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated task with new assignments

    Raises:
        HTTPException: 404 if group/task not found, 403 if not a member,
                      400 if assigned_user_ids contains non-members
    """
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

    # Validate: all assigned users must be group members
    assigned_user_ids = assignment_data.assigned_user_ids
    if assigned_user_ids:
        group_member_ids = {member.id for member in group.members}
        invalid_ids = set(assigned_user_ids) - group_member_ids

        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Users {list(invalid_ids)} are not members of this group"
            )

    # Delete all existing assignments
    db.execute(
        delete(task_assignments).where(task_assignments.c.task_id == task_id)
    )

    # Add new assignments
    if assigned_user_ids:
        for user_id in assigned_user_ids:
            db.execute(
                task_assignments.insert().values(
                    task_id=task_id,
                    user_id=user_id
                )
            )

    db.commit()
    db.refresh(task)

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    group_id: int,
    task_id: int,
    group: Group = Depends(get_current_group_member),
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
