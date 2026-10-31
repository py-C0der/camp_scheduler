from __future__ import annotations

import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Examination(Base):
    """Represents a midsem examination from the official CIT dataset."""
    __tablename__ = "examinations"

    id = Column(String(64), primary_key=True)
    course_ids_json = Column(Text, nullable=False)
    groups_json = Column(Text, nullable=False)
    size = Column(Integer, nullable=False)
    duration_hours = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assignments = relationship("ExaminationAssignment", back_populates="exam")


class ExaminationScheduleVersion(Base):
    """Tracks proposed vs approved versions of examination schedules."""
    __tablename__ = "exam_schedule_versions"

    id = Column(String(64), primary_key=True)  # e.g. "exam_ver_1", "exam_ver_2"
    version_number = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="proposed")  # proposed, approved, rejected, archived
    is_active = Column(Boolean, default=False)
    solver_status = Column(String(32), nullable=False)  # OPTIMAL, FEASIBLE
    solve_time_seconds = Column(Integer, default=0)
    soft_penalty = Column(Integer, default=0)
    created_by = Column(String(64), default="admin")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assignments = relationship("ExaminationAssignment", back_populates="schedule_version")
    approvals = relationship("ExaminationApproval", back_populates="schedule_version")
    validation_reports = relationship("ExaminationValidationReport", back_populates="schedule_version")


class ExaminationAssignment(Base):
    """Represents an examination placed at a specific day and session slot."""
    __tablename__ = "exam_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(String(64), ForeignKey("exam_schedule_versions.id", ondelete="CASCADE"), nullable=False)
    exam_id = Column(String(64), ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    day = Column(String(16), nullable=False)  # MON, TUE, WED, THU, FRI, SAT
    session = Column(String(16), nullable=False)  # AM, PM
    is_multi_room = Column(Boolean, default=False)
    total_effective_seats = Column(Integer, default=0)

    exam = relationship("Examination", back_populates="assignments")
    schedule_version = relationship("ExaminationScheduleVersion", back_populates="assignments")
    room_allocations = relationship("ExaminationRoomAllocation", back_populates="assignment")


class ExaminationRoomAllocation(Base):
    """Represents an allocated room for an examination assignment."""
    __tablename__ = "exam_room_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("exam_assignments.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(String(64), nullable=False)
    effective_seats = Column(Integer, nullable=False)

    assignment = relationship("ExaminationAssignment", back_populates="room_allocations")


class ExaminationValidationReport(Base):
    """Stores independent validation reports for examination schedules."""
    __tablename__ = "exam_validation_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(String(64), ForeignKey("exam_schedule_versions.id", ondelete="CASCADE"), nullable=False)
    is_valid = Column(Boolean, nullable=False)
    hard_violation_count = Column(Integer, default=0)
    hard_violations_json = Column(Text, nullable=True)
    soft_penalty = Column(Integer, default=0)
    validated_at = Column(DateTime, default=datetime.datetime.utcnow)

    schedule_version = relationship("ExaminationScheduleVersion", back_populates="validation_reports")


class ExaminationApproval(Base):
    """Records administrative approvals of examination schedules."""
    __tablename__ = "exam_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(String(64), ForeignKey("exam_schedule_versions.id", ondelete="CASCADE"), nullable=False)
    approved_by = Column(String(64), nullable=False)
    approved_at = Column(DateTime, default=datetime.datetime.utcnow)
    approval_notes = Column(Text, nullable=True)

    schedule_version = relationship("ExaminationScheduleVersion", back_populates="approvals")
