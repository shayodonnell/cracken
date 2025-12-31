"""Group management endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, insert, delete, update, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.group import Group, group_members
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupJoin,
    GroupMemberResponse
)
from app.utils.invite_code import generate_invite_code

router = APIRouter()


def get_member_count(group_id: int, db: Session) -> int:
    """Get the number of members in a group."""
    count = db.execute(
        select(func.count()).select_from(group_members).where(
            group_members.c.group_id == group_id
        )
    ).scalar()
    return count or 0


def promote_oldest_member(group_id: int, exclude_user_id: int, db: Session) -> int:
    """
    Promote the oldest member to admin.

    Args:
        group_id: ID of the group
        exclude_user_id: User ID to exclude from promotion (the leaving admin)
        db: Database session

    Returns:
        User ID of the new admin, or None if no other members exist
    """
    # Find oldest member (excluding current admin)
    oldest = db.execute(
        select(group_members.c.user_id)
        .where(
            group_members.c.group_id == group_id,
            group_members.c.user_id != exclude_user_id
        )
        .order_by(group_members.c.joined_at.asc())
        .limit(1)
    ).scalar()

    if not oldest:
        return None

    # Update role to admin
    db.execute(
        update(group_members)
        .where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == oldest
        )
        .values(role="admin")
    )

    # Update group creator
    group = db.query(Group).filter(Group.id == group_id).first()
    if group:
        group.created_by = oldest

    return oldest


def verify_group_membership(group_id: int, user_id: int, db: Session) -> Group:
    """
    Verify that a user is a member of a group and return the group.

    Args:
        group_id: ID of the group
        user_id: ID of the user
        db: Database session

    Returns:
        Group object if user is a member

    Raises:
        HTTPException: 404 if group not found, 403 if user not a member
    """
    # Get group
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


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new group.

    The authenticated user becomes the creator and first member of the group.
    A unique invite code is generated for others to join.

    Args:
        group_data: Group creation data (name)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created group with invite code

    Raises:
        HTTPException: If invite code generation fails after retries
    """
    # Retry logic for unique invite code
    max_attempts = 5
    invite_code = None

    for attempt in range(max_attempts):
        invite_code = generate_invite_code()

        # Check if code already exists
        existing = db.query(Group).filter(Group.invite_code == invite_code).first()
        if not existing:
            break

        if attempt == max_attempts - 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate unique invite code"
            )

    # Create group
    new_group = Group(
        name=group_data.name,
        invite_code=invite_code,
        created_by=current_user.id
    )

    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    # Add creator to group_members with admin role
    stmt = insert(group_members).values(
        user_id=current_user.id,
        group_id=new_group.id,
        joined_at=datetime.utcnow(),
        role="admin"
    )
    db.execute(stmt)
    db.commit()

    return new_group


@router.get("", response_model=List[GroupResponse])
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all groups the current user is a member of.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of groups the user belongs to
    """
    # Query groups where user is a member
    groups = db.query(Group).join(
        group_members
    ).filter(
        group_members.c.user_id == current_user.id
    ).all()

    return groups


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific group.

    Args:
        group_id: ID of the group
        current_user: Authenticated user
        db: Database session

    Returns:
        Group details

    Raises:
        HTTPException: 404 if group not found, 403 if not a member
    """
    group = verify_group_membership(group_id, current_user.id, db)
    return group


@router.post("/join", response_model=GroupResponse, status_code=status.HTTP_200_OK)
def join_group(
    join_data: GroupJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Join a group using an invite code.

    Args:
        join_data: Contains the invite code
        current_user: Authenticated user
        db: Database session

    Returns:
        The group that was joined

    Raises:
        HTTPException: 404 if invite code invalid, 400 if already a member
    """
    # Find group by invite code
    group = db.query(Group).filter(
        Group.invite_code == join_data.invite_code
    ).first()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code"
        )

    # Check if already a member
    existing_membership = db.execute(
        select(group_members).where(
            group_members.c.group_id == group.id,
            group_members.c.user_id == current_user.id
        )
    ).first()

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this group"
        )

    # Add user to group
    stmt = insert(group_members).values(
        user_id=current_user.id,
        group_id=group.id,
        joined_at=datetime.utcnow(),
        role="member"
    )
    db.execute(stmt)
    db.commit()

    # Refresh to get updated relationships
    db.refresh(group)

    return group


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
def list_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all members of a group.

    Args:
        group_id: ID of the group
        current_user: Authenticated user
        db: Database session

    Returns:
        List of group members with join dates

    Raises:
        HTTPException: 404 if group not found, 403 if not a member
    """
    # Verify membership
    verify_group_membership(group_id, current_user.id, db)

    # Query members with their join dates
    members_query = db.query(
        User.id,
        User.email,
        User.name,
        group_members.c.joined_at
    ).join(
        group_members,
        User.id == group_members.c.user_id
    ).filter(
        group_members.c.group_id == group_id
    ).all()

    # Convert to response format
    members = [
        GroupMemberResponse(
            id=member.id,
            email=member.email,
            name=member.name,
            joined_at=member.joined_at
        )
        for member in members_query
    ]

    return members


@router.delete("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Leave a group (self-removal).

    Any member can leave a group. If the leaving member is an admin,
    the oldest remaining member is promoted to admin. If the leaving member
    is the last member, the group is automatically deleted.

    Args:
        group_id: ID of the group to leave
        current_user: Authenticated user
        db: Database session

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if group not found, 403 if not a member
    """
    # Verify group exists and user is a member
    group = verify_group_membership(group_id, current_user.id, db)

    # Check member count
    member_count = get_member_count(group_id, db)

    if member_count == 1:
        # Last member leaving - delete the group
        db.delete(group)
        db.commit()
        return None

    # Check if current user is admin
    current_role = db.execute(
        select(group_members.c.role).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == current_user.id
        )
    ).scalar()

    # If admin is leaving, promote oldest member
    if current_role == "admin":
        promote_oldest_member(group_id, current_user.id, db)

    # Remove current user from group
    db.execute(
        delete(group_members).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == current_user.id
        )
    )
    db.commit()

    return None


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a member from a group (admin-only).

    Only admins can remove members. If the admin removes themselves,
    admin succession occurs. If removing the last member would empty
    the group, the group is automatically deleted.

    Args:
        group_id: ID of the group
        user_id: ID of the user to remove
        current_user: Authenticated user (must be admin)
        db: Database session

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if group not found, 403 if not admin, 404 if target user not a member
    """
    # Verify group exists and current user is a member
    group = verify_group_membership(group_id, current_user.id, db)

    # Verify current user is an admin
    current_role = db.execute(
        select(group_members.c.role).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == current_user.id
        )
    ).scalar()

    if current_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group admins can remove members"
        )

    # Verify target user is a member of the group
    target_membership = db.execute(
        select(group_members.c.user_id).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id
        )
    ).scalar()

    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this group"
        )

    # If admin is removing themselves, use leave logic
    if user_id == current_user.id:
        # Check member count
        member_count = get_member_count(group_id, db)

        if member_count == 1:
            # Last member leaving - delete the group
            db.delete(group)
            db.commit()
            return None

        # Admin removing self - promote oldest member
        promote_oldest_member(group_id, current_user.id, db)

    # Remove the target user from group
    db.execute(
        delete(group_members).where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id
        )
    )
    db.commit()

    return None
