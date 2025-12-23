from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.database import Base


# Association table for many-to-many relationship between users and groups
group_members = Table(
    "group_members",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("joined_at", DateTime, default=datetime.utcnow, nullable=False),
    Column("role", String(20), default="member", nullable=False),
)


class Group(Base):
    """Group model representing household groups."""

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(20), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    # Many-to-many with users through group_members association table
    members = relationship("User", secondary="group_members", back_populates="groups")

    # One-to-many with tasks
    tasks = relationship("Task", back_populates="group", cascade="all, delete-orphan")

    # Many-to-one with creator
    creator = relationship("User", foreign_keys=[created_by])
