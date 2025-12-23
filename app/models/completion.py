from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Completion(Base):
    """Completion model tracking when users complete tasks."""

    __tablename__ = "completions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Denormalized for query performance - makes rotation logic faster
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    task = relationship("Task", back_populates="completions")
    user = relationship("User", back_populates="completions")
    group = relationship("Group")

    # Indexes for optimized queries
    __table_args__ = (
        # Composite index for finding most recent completion per task
        Index("ix_completions_task_time", "task_id", "completed_at"),
        # Composite index for user completion history in a group
        Index("ix_completions_group_user_time", "group_id", "user_id", "completed_at"),
    )
