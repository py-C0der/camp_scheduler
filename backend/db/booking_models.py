"""
SQLAlchemy ORM Models for Module 4: Smart Venue Booking and Approval Management System.
Supports PostgreSQL and SQLite database engines.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class BookingRequestModel(Base):
    """Stores all submitted booking requests (historical and new)."""
    __tablename__ = "booking_requests"

    id = Column(String(50), primary_key=True, index=True)
    raw_text = Column(Text, nullable=True)
    title = Column(String(200), nullable=True)
    requester = Column(String(150), nullable=True)
    role = Column(String(50), nullable=False)  # admin, dept_coordinator, faculty, club
    department = Column(String(100), nullable=True)
    requested_category = Column(String(50), nullable=False)  # institute_event, guest_lecture, department_event, club_event
    effective_category = Column(String(50), nullable=False)
    attendance = Column(Integer, nullable=False)
    duration_periods = Column(Integer, nullable=False)
    room_types_json = Column(Text, nullable=False)  # JSON array
    windows_json = Column(Text, nullable=False)  # JSON array of {day, from_period, to_period}
    needs_json = Column(Text, nullable=False)  # JSON array
    mandatory_for_groups_json = Column(Text, nullable=False)  # JSON array
    requested_room = Column(String(50), nullable=True)
    series_id = Column(String(50), nullable=True)
    submitted_at = Column(String(50), nullable=False)
    created_by = Column(String(50), nullable=True)

    # Current Decision State
    status = Column(String(30), nullable=False, default="pending")  # pending, approved, rejected, alternative_offered, cancelled
    assigned_room_id = Column(String(50), nullable=True)
    assigned_day = Column(String(10), nullable=True)
    assigned_start_period = Column(Integer, nullable=True)
    assigned_end_period = Column(Integer, nullable=True)
    decision_reason = Column(Text, nullable=True)
    decision_by = Column(String(50), nullable=True)
    decision_at = Column(DateTime, nullable=True)

    # Cancellation Metadata
    is_cancelled = Column(Boolean, default=False)
    cancelled_at = Column(String(50), nullable=True)
    cancelled_by = Column(String(150), nullable=True)
    cancellation_note = Column(Text, nullable=True)

    # Relationships
    decisions = relationship("BookingDecisionModel", back_populates="booking", cascade="all, delete-orphan")
    alternatives = relationship("BookingAlternativeModel", back_populates="booking", cascade="all, delete-orphan")
    conflicts = relationship("BookingConflictModel", back_populates="booking", cascade="all, delete-orphan")
    audit_logs = relationship("BookingAuditLogModel", back_populates="booking", cascade="all, delete-orphan")


class BookingDraftModel(Base):
    """Stores intermediate natural language drafts before user confirms submission."""
    __tablename__ = "booking_drafts"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_json = Column(Text, nullable=False)  # JSON representation of extracted fields
    user_edits_json = Column(Text, nullable=True)
    status = Column(String(30), default="draft")  # draft, submitted, discarded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BookingAlternativeModel(Base):
    """Stores feasible alternative venue/slot suggestions when original request is unavailable."""
    __tablename__ = "booking_alternatives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(String(50), ForeignKey("booking_requests.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(String(50), nullable=False)
    day = Column(String(10), nullable=False)
    start_period = Column(Integer, nullable=False)
    end_period = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    features_json = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="offered")  # offered, accepted, declined, expired
    offered_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)

    booking = relationship("BookingRequestModel", back_populates="alternatives")


class BookingDecisionModel(Base):
    """Historical ledger of all decisions made for requests."""
    __tablename__ = "booking_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(String(50), ForeignKey("booking_requests.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), nullable=False)  # approved, rejected, alternative_offered
    room_id = Column(String(50), nullable=True)
    day = Column(String(10), nullable=True)
    start_period = Column(Integer, nullable=True)
    end_period = Column(Integer, nullable=True)
    decision_reason = Column(Text, nullable=False)
    decided_by = Column(String(50), nullable=False)
    decided_at = Column(DateTime, default=datetime.utcnow)

    booking = relationship("BookingRequestModel", back_populates="decisions")


class BookingPriorityConfigurationModel(Base):
    """Configurable priority rules ledger."""
    __tablename__ = "booking_priority_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, nullable=False, unique=True)
    priority_order_json = Column(Text, nullable=False)  # JSON array
    role_caps_json = Column(Text, nullable=False)  # JSON dict
    updated_by = Column(String(50), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class BookingConflictModel(Base):
    """Records detected conflicts preventing request approval."""
    __tablename__ = "booking_conflicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(String(50), ForeignKey("booking_requests.id", ondelete="CASCADE"), nullable=False)
    conflict_type = Column(String(50), nullable=False)  # room_busy, group_busy, room_unavailable, capacity_shortage, missing_features
    conflicting_entity_id = Column(String(100), nullable=True)
    conflict_details = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)

    booking = relationship("BookingRequestModel", back_populates="conflicts")


class BookingAuditLogModel(Base):
    """Immutable audit trail for all booking actions."""
    __tablename__ = "booking_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(String(50), ForeignKey("booking_requests.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(String(50), nullable=False)
    user_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    details_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    booking = relationship("BookingRequestModel", back_populates="audit_logs")
