from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model representing app users."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # Many-to-many with groups through group_members association table
    groups = relationship("Group", secondary="group_members", back_populates="members")

    # One-to-many with completions
    completions = relationship("Completion", back_populates="user")

    # Many-to-many with tasks (assigned tasks)
    assigned_tasks = relationship(
        "Task",
        secondary="task_assignments",  # Reference by string to avoid circular import
        back_populates="assigned_users"
    )
