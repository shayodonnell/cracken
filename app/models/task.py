from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Task(Base):
    """Task model representing chores/tasks within a group."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    emoji = Column(String(10), nullable=True)  # Unicode emoji representation
    category = Column(String(50), nullable=True)  # e.g., 'cleaning', 'cooking', 'pets'
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Soft delete capability

    # Relationships
    # Many-to-one with group
    group = relationship("Group", back_populates="tasks")

    # One-to-many with completions
    completions = relationship("Completion", back_populates="task", cascade="all, delete-orphan")
