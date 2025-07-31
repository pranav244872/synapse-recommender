# app/models.py

from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (BigInteger, Boolean, Enum, ForeignKey, String,
                        Text, TIMESTAMP)
from sqlalchemy.orm import (Mapped, declarative_base, mapped_column,
                            relationship)

# --- Base Class for Declarative Models ---
Base = declarative_base()

# --- Model Definitions ---

class Team(Base):
    __tablename__ = 'teams'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    manager_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'), unique=True)

    manager: Mapped[User] = relationship(foreign_keys=[manager_id], back_populates="managed_team", uselist=False)
    members: Mapped[List[User]] = relationship(foreign_keys="User.team_id", back_populates="team")

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum('admin', 'manager', 'engineer', name='user_role'), nullable=False, default='engineer')
    team_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('teams.id', ondelete='SET NULL'))
    availability: Mapped[str] = mapped_column(Enum('available', 'busy', name='availability_status'), nullable=False, default='available')

    team: Mapped[Optional[Team]] = relationship(foreign_keys=[team_id], back_populates="members")
    managed_team: Mapped[Optional[Team]] = relationship(foreign_keys=[Team.manager_id], back_populates="manager", uselist=False)
    skills: Mapped[List[UserSkill]] = relationship(back_populates="user", cascade="all, delete-orphan")
    assigned_tasks: Mapped[List[Task]] = relationship(back_populates="assignee")

class Skill(Base):
    __tablename__ = 'skills'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class SkillAlias(Base):
    __tablename__ = 'skill_aliases'
    alias_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    skill_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('skills.id', ondelete='CASCADE'), nullable=False)

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('projects.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum('open', 'in_progress', 'done', name='task_status'), nullable=False, default='open')
    priority: Mapped[str] = mapped_column(Enum('low', 'medium', 'high', 'critical', name='task_priority'), nullable=False, default='medium')
    assignee_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    assignee: Mapped[Optional[User]] = relationship(back_populates="assigned_tasks")
    required_skills: Mapped[List[TaskRequiredSkill]] = relationship(back_populates="task", cascade="all, delete-orphan")

class UserSkill(Base):
    __tablename__ = 'user_skills'
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    skill_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)
    proficiency: Mapped[str] = mapped_column(Enum('beginner', 'intermediate', 'expert', name='proficiency_level'), nullable=False)

    user: Mapped[User] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()

class TaskRequiredSkill(Base):
    __tablename__ = 'task_required_skills'
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True)
    skill_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)

    task: Mapped[Task] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship()

class Invitation(Base):
    __tablename__ = 'invitations'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    invitation_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role_to_invite: Mapped[str] = mapped_column(Enum('admin', 'manager', 'engineer', name='user_role_invitation'), nullable=False)
    inviter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending')
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
